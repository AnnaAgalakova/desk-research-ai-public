"""Worker: takes new materials from the database, asks the model, writes findings.

This is the only place in the system where a model is called.
"""

import json
import os
import time
import urllib.request

import db

SERVICE = "worker"
MODEL = os.environ.get("MODEL", "anthropic/claude-haiku-5.5")
PROMPT_VERSION = "v2"
POLL_SECONDS = 10
RETRY_SECONDS = 3600

ENTITIES = [
    "OpenAI",
    "Anthropic",
    "Google",
    "Meta",
    "Microsoft",
    "Apple",
    "Nvidia",
    "DeepSeek",
    "Mistral",
    "xAI",
    "Яндекс",
    "Сбер",
]

PROMPT = """Ты помогаешь вести desk research по рынку разговоров об искусственном интеллекте.
Материал:
Заголовок: {title}
Текст: {text}

Ответь строго JSON без пояснений:
{{"about_ai": true или false — материал про искусственный интеллект,
  "entity": одна компания из списка {entities}, о которой материал, или null,
  "summary": "о чем материал, одна короткая фраза по-русски",
  "tone": целое число от 1 до 5 — отношение материала к ИИ в целом:
          1 критика или страх, 3 нейтрально, 5 оптимистично}}"""


def parse_tone(value):
    """Tone must be an integer 1..5; anything else (including bool, floats, text) becomes None."""
    if isinstance(value, bool):
        return None
    if isinstance(value, str) and value.isdigit():
        value = int(value)
    if isinstance(value, int) and 1 <= value <= 5:
        return value
    return None


def ask_model(title, text):
    body = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": PROMPT.format(
                    title=title, text=(text or "")[:2000], entities=", ".join(ENTITIES)
                ),
            }
        ],
        "response_format": {"type": "json_object"},
    }
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        content = json.loads(resp.read())["choices"][0]["message"]["content"]
    content = (
        content.strip().removeprefix("```json").removeprefix("```").removesuffix("```")
    )
    return json.loads(content)


def process_new(conn):
    pending = conn.execute(
        "SELECT id, title, text FROM materials WHERE status = 'new' ORDER BY id"
    ).fetchall()
    if not pending:
        return
    run_id = db.start_run(conn, SERVICE)
    found = 0
    for done, (material_id, title, text) in enumerate(pending, 1):
        try:
            answer = ask_model(title, text)
        except Exception as error:
            conn.execute(
                "UPDATE materials SET status = 'failed' WHERE id = %s", (material_id,)
            )
            db.log(SERVICE, f"материал {material_id}: модель не ответила: {error}")
            continue
        if answer.get("about_ai"):
            entity = answer.get("entity") if answer.get("entity") in ENTITIES else None
            conn.execute(
                """INSERT INTO findings (material_id, entity, summary, tone, model, prompt_version)
                   VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (material_id) DO NOTHING""",
                (
                    material_id,
                    entity,
                    answer["summary"],
                    parse_tone(answer.get("tone")),
                    MODEL,
                    PROMPT_VERSION,
                ),
            )
            conn.execute(
                "UPDATE materials SET status = 'done' WHERE id = %s", (material_id,)
            )
            found += 1
            db.log(
                SERVICE,
                f"материал {material_id} -> находка ({entity or 'без компании'}): {answer['summary']}",
            )
        else:
            conn.execute(
                "UPDATE materials SET status = 'skipped' WHERE id = %s", (material_id,)
            )
            db.log(SERVICE, f"материал {material_id} не про AI, пропускаю")
        if done % 10 == 0:
            db.progress_run(
                conn, SERVICE, run_id, found, f"разобрано {done} из {len(pending)}"
            )
    db.finish_run(
        conn, SERVICE, run_id, found, f"разобрано {len(pending)}, находок {found}"
    )


def retry_failed(conn):
    retried = conn.execute(
        "UPDATE materials SET status = 'new' WHERE status = 'failed'"
    ).rowcount
    if retried:
        db.log(
            SERVICE,
            f"вернул в разбор {retried} материалов, на которых модель не ответила",
        )


def main():
    conn = db.connect()
    db.init_schema(conn)
    db.log(SERVICE, f"жду новые материалы в базе, модель {MODEL}")
    last_retry = float("-inf")
    while True:
        try:
            # materials the model failed on go back into the queue once an hour
            if time.monotonic() - last_retry >= RETRY_SECONDS:
                retry_failed(conn)
                last_retry = time.monotonic()
            process_new(conn)
        except Exception as error:
            db.log(SERVICE, f"упал: {error}")
            conn = db.connect()
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
