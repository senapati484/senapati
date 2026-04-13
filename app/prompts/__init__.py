from datetime import datetime
import platform
import psutil
import json
import re

from .playbook import (
    WAKE_ACK_PROMPT,
    CORE_SYSTEM_PROMPT,
    TOOL_ROUTING_PROMPT,
    APPROVAL_GATE_PROMPT,
    OCR_INTERPRET_PROMPT,
    MORNING_BRIEF_PROMPT,
    MULTI_STEP_PROMPT,
    FACT_EXTRACTION_PROMPT,
    ERROR_RECOVERY_PROMPT,
    ONBOARDING_PROMPT,
    HABIT_SUGGEST_PROMPT,
    SESSION_SUMMARY_PROMPT,
    TRAINING_DATA_GEN_PROMPT,
    PLUGIN_SETUP_PROMPT,
    UNDO_PROMPT,
    CONTEXT_BRIDGE_PROMPT,
    NOTIFICATION_TRIAGE_PROMPT,
    EOD_BRIEF_PROMPT,
    CODE_EXPLAIN_PROMPT,
    FEW_SHOT_EXAMPLES,
)

def get_system_info():
    return {
        "os_name": platform.system(),
        "os_version": platform.mac_ver()[0] if platform.system() == "Darwin" else platform.release(),
        "chip": "Apple Silicon" if platform.system() == "Darwin" and platform.machine() == "arm64" else platform.processor(),
        "ram_gb": round(psutil.virtual_memory().total / 1e9),
    }

def build_wake_ack_prompt(user_name: str = "there") -> str:
    from .playbook import WAKE_ACK_PROMPT
    return WAKE_ACK_PROMPT.replace("{{USER_NAME}}", user_name).replace(
        "{{CURRENT_TIME}}", datetime.now().strftime("%I:%M %p")
    )

def build_system_prompt(
    user_name: str = "there",
    memory_context: str = "",
    session_history: str = "",
    turn_count: int = 0,
    pending_tasks: str = "",
    user_facts: str = "",
    uptime: str = "0m"
) -> str:
    from .playbook import CORE_SYSTEM_PROMPT
    info = get_system_info()
    prompt = CORE_SYSTEM_PROMPT
    prompt = prompt.replace("{{USER_NAME}}", user_name)
    prompt = prompt.replace("{{OS_NAME}}", info["os_name"])
    prompt = prompt.replace("{{OS_VERSION}}", info["os_version"])
    prompt = prompt.replace("{{CHIP}}", info["chip"])
    prompt = prompt.replace("{{RAM_GB}}", str(info["ram_gb"]))
    prompt = prompt.replace("{{CURRENT_TIME}}", datetime.now().strftime("%I:%M %p"))
    prompt = prompt.replace("{{CURRENT_WEEKDAY}}", datetime.now().strftime("%A"))
    prompt = prompt.replace("{{UPTIME}}", uptime or "0m")
    prompt = prompt.replace("{{MEMORY_CONTEXT}}", memory_context or "(no memory)")
    prompt = prompt.replace("{{SESSION_HISTORY}}", session_history or "(no prior turns)")
    prompt = prompt.replace("{{TURN_COUNT}}", str(turn_count))
    prompt = prompt.replace("{{PENDING_TASKS}}", pending_tasks or "(no pending tasks)")
    prompt = prompt.replace("{{USER_FACTS}}", user_facts or "(no facts known)")
    return prompt

def build_tool_prompt(user_input: str, plugin_tools: str = "", disabled_tools: str = "") -> str:
    from .playbook import TOOL_ROUTING_PROMPT
    prompt = TOOL_ROUTING_PROMPT
    prompt = prompt.replace("{{USER_INPUT}}", user_input)
    prompt = prompt.replace("{{PLUGIN_TOOLS}}", plugin_tools or "(no plugins enabled)")
    prompt = prompt.replace("{{DISABLED_TOOLS}}", disabled_tools or "(none)")
    return prompt

def build_approval_prompt(action_desc: str, risk_level: str, action_context: str = "") -> str:
    from .playbook import APPROVAL_GATE_PROMPT
    prompt = APPROVAL_GATE_PROMPT
    prompt = prompt.replace("{{ACTION_DESCRIPTION}}", action_desc)
    prompt = prompt.replace("{{RISK_LEVEL}}", risk_level)
    prompt = prompt.replace("{{ACTION_CONTEXT}}", action_context or "None")
    return prompt

def build_ocr_prompt(user_question: str, ocr_text: str) -> str:
    from .playbook import OCR_INTERPRET_PROMPT
    prompt = OCR_INTERPRET_PROMPT
    prompt = prompt.replace("{{USER_QUESTION}}", user_question)
    prompt = prompt.replace("{{OCR_TEXT}}", ocr_text)
    return prompt

def build_morning_brief_prompt(
    user_name: str,
    date_string: str,
    calendar_events: str = "",
    git_status: str = "",
    notifications: str = "",
    battery: int = 100,
    pending_tasks: str = "",
    weather: str = ""
) -> str:
    from .playbook import MORNING_BRIEF_PROMPT
    prompt = MORNING_BRIEF_PROMPT
    prompt = prompt.replace("{{USER_NAME}}", user_name)
    prompt = prompt.replace("{{DATE_STRING}}", date_string)
    prompt = prompt.replace("{{CALENDAR_EVENTS}}", calendar_events or "(no events)")
    prompt = prompt.replace("{{GIT_STATUS_SUMMARY}}", git_status or "(no active PRs)")
    prompt = prompt.replace("{{NOTIFICATION_SUMMARY}}", notifications or "(none)")
    prompt = prompt.replace("{{BATTERY_PERCENT}}", str(battery))
    prompt = prompt.replace("{{PENDING_TASKS}}", pending_tasks or "(no pending)")
    prompt = prompt.replace("{{WEATHER}}", weather or "(unavailable)")
    return prompt

def build_multi_step_prompt(user_input: str, available_tools: str = "") -> str:
    from .playbook import MULTI_STEP_PROMPT
    prompt = MULTI_STEP_PROMPT
    prompt = prompt.replace("{{USER_INPUT}}", user_input)
    prompt = prompt.replace("{{AVAILABLE_TOOLS_BRIEF}}", available_tools or "open_app, close_app, run_shell, read_file, write_file")
    return prompt

def build_fact_extraction_prompt(session_text: str) -> str:
    from .playbook import FACT_EXTRACTION_PROMPT
    return FACT_EXTRACTION_PROMPT.replace("{{SESSION_TEXT}}", session_text)

def build_error_recovery_prompt(
    tool_name: str,
    tool_args: dict,
    error_type: str,
    error_message: str
) -> str:
    from .playbook import ERROR_RECOVERY_PROMPT
    prompt = ERROR_RECOVERY_PROMPT
    prompt = prompt.replace("{{TOOL_NAME}}", tool_name)
    prompt = prompt.replace("{{TOOL_ARGS}}", json.dumps(tool_args))
    prompt = prompt.replace("{{ERROR_TYPE}}", error_type)
    prompt = prompt.replace("{{ERROR_MESSAGE}}", error_message)
    return prompt

def build_onboarding_prompt(user_name: str, os_name: str, time_of_day: str) -> str:
    from .playbook import ONBOARDING_PROMPT
    prompt = ONBOARDING_PROMPT
    prompt = prompt.replace("{{USER_NAME}}", user_name)
    prompt = prompt.replace("{{OS_NAME}}", os_name)
    prompt = prompt.replace("{{TIME_OF_DAY}}", time_of_day)
    return prompt

def build_habit_suggest_prompt(
    user_name: str,
    habit_tool: str,
    habit_args: dict,
    habit_count: int,
    habit_weekday: str,
    habit_hour: int,
    current_time: str
) -> str:
    from .playbook import HABIT_SUGGEST_PROMPT
    prompt = HABIT_SUGGEST_PROMPT
    prompt = prompt.replace("{{USER_NAME}}", user_name)
    prompt = prompt.replace("{{HABIT_TOOL}}", habit_tool)
    prompt = prompt.replace("{{HABIT_ARGS}}", json.dumps(habit_args))
    prompt = prompt.replace("{{HABIT_COUNT}}", str(habit_count))
    prompt = prompt.replace("{{HABIT_WEEKDAY}}", habit_weekday)
    prompt = prompt.replace("{{HABIT_HOUR}}", str(habit_hour))
    prompt = prompt.replace("{{CURRENT_TIME}}", current_time)
    return prompt

def build_session_summary_prompt(
    full_session_text: str,
    session_date: str,
    session_duration: str
) -> str:
    from .playbook import SESSION_SUMMARY_PROMPT
    prompt = SESSION_SUMMARY_PROMPT
    prompt = prompt.replace("{{FULL_SESSION_TEXT}}", full_session_text)
    prompt = prompt.replace("{{SESSION_DATE}}", session_date)
    prompt = prompt.replace("{{SESSION_DURATION}}", session_duration)
    return prompt

def build_training_data_prompt(full_session_text: str) -> str:
    from .playbook import TRAINING_DATA_GEN_PROMPT
    return TRAINING_DATA_GEN_PROMPT.replace("{{FULL_SESSION_TEXT}}", full_session_text)

def build_plugin_setup_prompt(
    plugin_name: str,
    plugin_file: str,
    required_keys: str,
    plugin_desc: str
) -> str:
    from .playbook import PLUGIN_SETUP_PROMPT
    prompt = PLUGIN_SETUP_PROMPT
    prompt = prompt.replace("{{PLUGIN_NAME}}", plugin_name)
    prompt = prompt.replace("{{PLUGIN_FILE}}", plugin_file)
    prompt = prompt.replace("{{REQUIRED_CONFIG_KEYS}}", required_keys)
    prompt = prompt.replace("{{PLUGIN_DESCRIPTION}}", plugin_desc)
    return prompt

def build_undo_prompt(
    recent_actions: str,
    last_tool: str,
    last_args: dict,
    last_result: str,
    last_timestamp: str
) -> str:
    from .playbook import UNDO_PROMPT
    prompt = UNDO_PROMPT
    prompt = prompt.replace("{{RECENT_ACTION_LOG}}", recent_actions)
    prompt = prompt.replace("{{LAST_TOOL}}", last_tool)
    prompt = prompt.replace("{{LAST_ARGS}}", json.dumps(last_args))
    prompt = prompt.replace("{{LAST_RESULT}}", last_result)
    prompt = prompt.replace("{{LAST_TIMESTAMP}}", last_timestamp)
    return prompt

def build_context_bridge_prompt(
    user_input: str,
    session_history: str,
    memory_entities: str,
    last_file: str = "",
    last_project: str = "",
    last_person: str = "",
    last_entity: str = ""
) -> str:
    from .playbook import CONTEXT_BRIDGE_PROMPT
    prompt = CONTEXT_BRIDGE_PROMPT
    prompt = prompt.replace("{{USER_INPUT}}", user_input)
    prompt = prompt.replace("{{SESSION_HISTORY_LAST_4}}", session_history)
    prompt = prompt.replace("{{MEMORY_RECENT_ENTITIES}}", memory_entities)
    prompt = prompt.replace("{{LAST_MENTIONED_FILE}}", last_file or "None")
    prompt = prompt.replace("{{LAST_MENTIONED_PROJECT}}", last_project or "None")
    prompt = prompt.replace("{{LAST_MENTIONED_PERSON}}", last_person or "None")
    prompt = prompt.replace("{{LAST_MENTIONED_ENTITY}}", last_entity or "None")
    return prompt

def build_notification_triage_prompt(
    app: str,
    title: str,
    body: str,
    time: str,
    agent_state: str,
    user_activity: str,
    known_contacts: str = ""
) -> str:
    from .playbook import NOTIFICATION_TRIAGE_PROMPT
    prompt = NOTIFICATION_TRIAGE_PROMPT
    prompt = prompt.replace("{{NOTIF_APP}}", app)
    prompt = prompt.replace("{{NOTIF_TITLE}}", title)
    prompt = prompt.replace("{{NOTIF_BODY}}", body)
    prompt = prompt.replace("{{NOTIF_TIME}}", time)
    prompt = prompt.replace("{{AGENT_STATE}}", agent_state)
    prompt = prompt.replace("{{USER_CURRENT_ACTIVITY}}", user_activity)
    prompt = prompt.replace("{{KNOWN_CONTACTS}}", known_contacts or "none")
    return prompt

def build_eod_brief_prompt(
    user_name: str,
    session_count: int,
    command_count: int,
    tasks_done: int,
    tasks_pending: int,
    projects: str,
    commits: int,
    active_time: str
) -> str:
    from .playbook import EOD_BRIEF_PROMPT
    prompt = EOD_BRIEF_PROMPT
    prompt = prompt.replace("{{USER_NAME}}", user_name)
    prompt = prompt.replace("{{SESSION_COUNT}}", str(session_count))
    prompt = prompt.replace("{{COMMAND_COUNT}}", str(command_count))
    prompt = prompt.replace("{{TASKS_DONE}}", str(tasks_done))
    prompt = prompt.replace("{{TASKS_PENDING}}", str(tasks_pending))
    prompt = prompt.replace("{{PROJECTS_TODAY}}", projects or "none")
    prompt = prompt.replace("{{COMMIT_COUNT}}", str(commits))
    prompt = prompt.replace("{{ACTIVE_TIME}}", active_time)
    return prompt

def build_code_explain_prompt(
    user_question: str,
    code_text: str,
    file_path: str = "",
    language: str = ""
) -> str:
    from .playbook import CODE_EXPLAIN_PROMPT
    prompt = CODE_EXPLAIN_PROMPT
    prompt = prompt.replace("{{USER_QUESTION}}", user_question)
    prompt = prompt.replace("{{CODE_TEXT}}", code_text)
    prompt = prompt.replace("{{FILE_PATH}}", file_path or "unknown")
    prompt = prompt.replace("{{LANGUAGE}}", language or "unknown")
    return prompt


def parse_json_response(raw: str) -> dict:
    """
    Strips markdown fences, extracts JSON, falls back to chat if malformed.
    This runs after EVERY LLM call. Never skip it.
    """
    cleaned = re.sub(r'```(?:json)?\n?', '', raw).strip()
    match = re.search(r'\{.*\}', cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return {"tool": "chat", "args": {}, "speak": cleaned[:200]}