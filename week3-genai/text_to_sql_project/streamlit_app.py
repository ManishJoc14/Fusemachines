from __future__ import annotations

import json
from typing import Any

import httpx
import pandas as pd
import streamlit as st


st.set_page_config(
    page_title="SQL Agent Explorer",
    page_icon="",
    layout="wide",
)

# Minimal, high-contrast CSS
st.markdown(
    """
<style>
    /* Reset and Typography for visibility */
    .main {
        color: #0F172A;
    }
    
    /* Ensure code blocks are readable */
    .stCodeBlock {
        border-radius: 0.5rem;
    }
    
    /* Fix Tab contrast: Inactive is visible, Active is bold */
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre;
        font-size: 16px;
        font-weight: 400;
        color: #64748B;
    }
    .stTabs [aria-selected="true"] {
        color: #0F172A !important;
        font-weight: 600 !important;
    }
    
    /* Step Header Styling */
    .step-header {
        font-size: 1.1rem;
        font-weight: 700;
        color: #1E293B;
        margin-bottom: 0.5rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
</style>
""",
    unsafe_allow_html=True,
)


def stream_question(base_url: str, question: str):
    endpoint = f"{base_url.rstrip('/')}/agent/sql/stream"
    with httpx.stream("POST", endpoint, json={"question": question}, timeout=180.0) as response:
        for line in response.iter_lines():
            if line:
                yield json.loads(line)


def format_json(value: Any) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False, default=str)


def canonical_step_name(step_name: str) -> str:
    name = str(step_name or "step").strip().lower().replace(" ", "_")
    if name.endswith("_error"):
        name = name[:-6]
    return name


def step_key(update: dict[str, Any]) -> str:
    name = canonical_step_name(str(update.get("step") or "step"))
    attempt = update.get("attempt")
    if attempt is None:
        return name
    return f"{name}:{attempt}"


def step_title(step_name: str) -> str:
    return step_name.replace("_", " ").title() or "Step"


def step_status_icon(status: str, error: Any) -> str:
    if error:
        return "❌"
    if status in {"running", "in_progress", "in-progress"}:
        return "⏳"
    if status in {"queued", "pending"}:
        return "🕓"
    return "✅"


def merge_step(existing: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
    merged = dict(existing)
    for key, value in update.items():
        if value is not None:
            merged[key] = value
    merged.setdefault("status", "done")
    merged["key"] = existing.get("key") or update.get("key") or step_key(update)
    merged.setdefault("events", existing.get("events", []))
    return merged


def render_step_card(step: dict[str, Any]) -> None:
    name = step_title(canonical_step_name(str(step.get("step", "Step"))))
    status = str(step.get("status", "done"))
    icon = step_status_icon(status, step.get("error"))
    events = step.get("events") or [step]
    latest_event = events[-1] if events else step

    header = f"{icon} {name}"
    attempt = latest_event.get("attempt")
    if attempt is not None:
        header += f" · Attempt {attempt}"

    with st.container(border=True):
        st.markdown(f"<div class='step-header'>{header}</div>", unsafe_allow_html=True)

        st.caption(f"Status: {status.replace('_', ' ').title()}")
        stage_text = latest_event.get("message") or latest_event.get("stage") or latest_event.get("detail")
        if stage_text:
            st.write(stage_text)

        left, right = st.columns(2)

        with left:
            st.caption("Input")
            input_payload = next((ev.get("messages") for ev in events if ev.get("messages") is not None), None)
            if input_payload is not None:
                render_json_value(input_payload)
            elif latest_event.get("input") is not None:
                render_json_value(latest_event["input"])
            else:
                st.write("Prompts were not captured for this step.")

        with right:
            st.caption("Agent Output")
            if latest_event.get("plan") is not None:
                st.json(latest_event["plan"])
            elif latest_event.get("sql") is not None:
                st.code(latest_event["sql"], language="sql")
            elif latest_event.get("repaired_sql") is not None:
                st.code(latest_event["repaired_sql"], language="sql")
            elif latest_event.get("result_preview") is not None:
                st.dataframe(pd.DataFrame(latest_event["result_preview"]), width="stretch", hide_index=True)
            elif latest_event.get("result") is not None:
                render_result(latest_event["result"])
            elif latest_event.get("result_count") is not None:
                st.write(f"Database returned {latest_event['result_count']} row(s).")
            elif status in {"running", "in_progress", "in-progress"}:
                st.info("Working on this step...")
            else:
                st.info("No output yet.")

        if latest_event.get("error") is not None:
            st.error(latest_event["error"])


def render_result(result: Any) -> None:
    if result is None:
        st.info("No data returned.")
        return

    if isinstance(result, list) and result and isinstance(result[0], dict):
        st.dataframe(pd.DataFrame(result), width="stretch", hide_index=True)
    elif isinstance(result, dict):
        st.json(result)
    else:
        st.write(result)


def render_json_value(value: Any) -> None:
    if isinstance(value, (dict, list)):
        st.json(value)
    else:
        st.code(format_json(value), language="json")


# --- MAIN UI ---

st.title("SQL Agent Explorer")
st.caption("Detailed step-by-step agentic reasoning and execution.")
st.write("") # Spacer

# API Settings
with st.expander("⚙️ Connection Settings", expanded=False):
    base_url = st.text_input("FastAPI base URL", value="http://app:8000")
    st.caption("Use the Docker service name when Streamlit runs in Compose, or localhost when running locally.")

question = st.text_area(
    "User Prompt",
    value="Customers from France",
    height=80,
    placeholder="e.g., 'What are the top 5 products by sales?'",
)

if st.button("Generate Solution", type="primary"):
    if not question.strip():
        st.warning("Please enter a question.")
    else:
        st.session_state["last_result"] = None
        st.session_state["live_trace"] = []
        st.session_state["live_trace_index"] = {}

        trace_placeholder = st.empty()
        
        try:
            final_result = None
            
            with st.status("🤖 Agent is working...", expanded=True) as status_box:
                for update in stream_question(base_url, question.strip()):
                    key = step_key(update)
                    update["key"] = key

                    trace_index = st.session_state["live_trace_index"]
                    existing = trace_index.get(key)
                    if existing is None:
                        trace_index[key] = {**update, "events": [dict(update)]}
                        st.session_state["live_trace"].append(trace_index[key])
                    else:
                        merged = merge_step(existing, update)
                        merged["events"] = list(existing.get("events", [])) + [dict(update)]
                        trace_index[key] = merged
                        for idx, step in enumerate(st.session_state["live_trace"]):
                            if step.get("key") == key:
                                st.session_state["live_trace"][idx] = merged
                                break

                    with trace_placeholder.container():
                        st.subheader("Agent Trace")
                        st.caption("Each logical step appears once. Retry and error events stay inside the same card.")
                        for step in st.session_state["live_trace"]:
                            render_step_card(step)

                    if "final_response" in update:
                        final_result = update["final_response"]
                
                if final_result:
                    status_box.update(label="✅ Query Complete", state="complete", expanded=False)
                    st.session_state["last_result"] = final_result
                    st.session_state["last_question"] = question.strip()
                    with trace_placeholder.container():
                        st.subheader("Agent Trace")
                        st.caption("Final trace for the completed request.")
                        for step in st.session_state["live_trace"]:
                            render_step_card(step)
                else:
                    status_box.update(label="❌ Agent Failed", state="error", expanded=True)

        except Exception as exc:
            st.error(f"Execution Error: {exc}")

# Show persistent results (Final Output)
result = st.session_state.get("last_result")
if result:
    res_status = result.get("status", "failed")
    st.markdown("---")
    
    # Final Result Tabs
    tab_result, tab_sql, tab_raw = st.tabs(["📊 Final Result", "📝 Full SQL Query", "🔍 Raw API Output"])

    with tab_result:
        if res_status == "success":
            st.subheader("Summary")
            st.write(result.get("summary") or "Result generated successfully.")
            st.subheader("Data")
            render_result(result.get("result"))
        else:
            st.error(f"Processing Failed: {result.get('error')}")

    with tab_sql:
        sql = result.get("sql")
        if sql:
            st.code(sql, language="sql")
        else:
            st.info("No SQL query was generated.")

    with tab_raw:
        st.json(result)
