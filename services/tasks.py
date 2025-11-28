from .llm import complete
import re

SYS = (
    "You are a task extraction assistant. "
    "Given an email body, extract actionable tasks and due dates if mentioned. "
    "Respond in this format:\n"
    "- [ ] Task description [due: <date?>]"
)

async def extract_tasks(body: str):
    prompt = f"Email Body:\n{body}\n\nReturn tasks in checkbox format:"
    raw = await complete(SYS, prompt)

    # Parse out task lines
    tasks = []
    for line in raw.splitlines():
        line = line.strip()
        if line.startswith("- [ ]"):
            m = re.search(r"\[due:\s*(.*?)\]", line)
            due = m.group(1) if m else None
            text = line.replace("- [ ]", "").split("[due:")[0].strip()
            tasks.append({"task": text, "due": due})
    return tasks
