
import streamlit as st
import sqlite3
import json
import os
import re
from datetime import datetime

# ============================================================
# DEVHANDOVER AI - IMPROVEMENT 2
# AI-POWERED KNOWLEDGE GAP DETECTION
# ============================================================

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "knowledge_gaps.db")

MODEL_NAME = "gemini-2.0-flash"

KNOWLEDGE_AREAS = {
    "Architecture": (
        "Explain the overall system architecture, major components, "
        "their responsibilities, and how they communicate."
    ),
    "Database": (
        "Explain the database structure, important tables, relationships, "
        "data flow, migrations, and backup procedures."
    ),
    "APIs and Integrations": (
        "Explain the important APIs, endpoints, integrations, authentication, "
        "request formats, and error handling."
    ),
    "Deployment": (
        "Explain how the application is deployed, configured, monitored, "
        "updated, and rolled back."
    ),
    "Security": (
        "Explain authentication, authorization, sensitive data handling, "
        "security controls, and known security concerns."
    ),
    "Debugging and Troubleshooting": (
        "Explain common failures, how to identify them, debugging steps, "
        "logs, and recovery procedures."
    ),
    "Business Logic": (
        "Explain the main workflows, important business rules, edge cases, "
        "and decisions behind the implementation."
    ),
    "Dependencies": (
        "Explain external libraries, services, dependencies, versions, "
        "and what would happen if a dependency became unavailable."
    ),
    "Testing": (
        "Explain the testing strategy, test cases, test environments, "
        "known limitations, and how to run tests."
    ),
    "Other": (
        "Explain important project knowledge that does not fit into "
        "the other technical areas."
    )
}

# ============================================================
# DATABASE
# ============================================================

def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    connection = get_connection()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_gaps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_name TEXT NOT NULL,
            contributor TEXT NOT NULL,
            knowledge_area TEXT NOT NULL,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            completeness INTEGER DEFAULT 0,
            severity TEXT DEFAULT 'Medium',
            gap_summary TEXT,
            follow_up TEXT,
            status TEXT DEFAULT 'Open',
            created_at TEXT NOT NULL
        )
    """)

    connection.commit()
    connection.close()


def save_analysis(project, contributor, domain, question, answer, result):
    connection = get_connection()

    connection.execute("""
        INSERT INTO knowledge_gaps (
            project_name,
            contributor,
            knowledge_area,
            question,
            answer,
            completeness,
            severity,
            gap_summary,
            follow_up,
            status,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        project,
        contributor,
        domain,
        question,
        answer,
        result["completeness"],
        result["severity"],
        result["gap_summary"],
        result["follow_up"],
        "Open" if result["severity"] != "Low" else "Under Review",
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    connection.commit()
    connection.close()


def get_all_gaps(project=None):
    connection = get_connection()

    if project:
        rows = connection.execute("""
            SELECT * FROM knowledge_gaps
            WHERE project_name = ?
            ORDER BY created_at DESC
        """, (project,)).fetchall()
    else:
        rows = connection.execute("""
            SELECT * FROM knowledge_gaps
            ORDER BY created_at DESC
        """).fetchall()

    connection.close()
    return [dict(row) for row in rows]


def update_gap_status(gap_id, status):
    connection = get_connection()

    connection.execute("""
        UPDATE knowledge_gaps
        SET status = ?
        WHERE id = ?
    """, (status, gap_id))

    connection.commit()
    connection.close()


# ============================================================
# GEMINI CONFIGURATION
# ============================================================

def get_gemini_api_key():
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        try:
            api_key = st.secrets.get("GEMINI_API_KEY")
        except Exception:
            pass

    return api_key


def call_gemini(prompt):
    """
    Supports both the newer google-genai SDK and
    the older google-generativeai SDK.
    """

    api_key = get_gemini_api_key()

    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY is missing. Configure your Gemini API key."
        )

    # New Google Gen AI SDK
    try:
        from google import genai

        client = genai.Client(api_key=api_key)

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt
        )

        return response.text

    except ImportError:
        pass

    # Older Google Generative AI SDK
    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)

        model = genai.GenerativeModel("gemini-1.5-flash")

        response = model.generate_content(prompt)

        return response.text

    except ImportError:
        raise ImportError(
            "Install either google-genai or google-generativeai."
        )


# ============================================================
# RESPONSE PARSING
# ============================================================

def extract_json(response):
    """
    Extract JSON even if Gemini wraps the response
    in Markdown code fences.
    """

    response = response.strip()

    response = re.sub(
        r"^```(?:json)?\s*",
        "",
        response,
        flags=re.IGNORECASE
    )

    response = re.sub(r"\s*```$", "", response)

    start = response.find("{")
    end = response.rfind("}")

    if start == -1 or end == -1:
        raise ValueError("Gemini did not return valid JSON.")

    return json.loads(response[start:end + 1])


def normalize_result(data):
    severity = str(data.get("severity", "Medium")).title()

    if severity not in ["High", "Medium", "Low"]:
        severity = "Medium"

    try:
        completeness = int(data.get("completeness", 50))
    except (ValueError, TypeError):
        completeness = 50

    completeness = max(0, min(100, completeness))

    return {
        "completeness": completeness,
        "severity": severity,
        "gap_summary": str(
            data.get("gap_summary", "Further verification is required.")
        ),
        "missing_information": data.get(
            "missing_information", []
        ),
        "follow_up": str(
            data.get(
                "follow_up",
                "Can you explain this area in more detail?"
            )
        ),
        "reason": str(
            data.get("reason", "Additional information may be needed.")
        ),
        "status": str(data.get("status", "Needs review"))
    }


# ============================================================
# FALLBACK EVALUATION
# Used when Gemini is unavailable.
# This is rule-based, NOT AI evaluation.
# ============================================================

def fallback_evaluation(answer, domain):
    words = answer.split()
    word_count = len(words)

    if word_count < 10:
        completeness = 15
        severity = "High"
        gap_summary = (
            "The answer is too short to establish sufficient "
            "project knowledge."
        )
        missing = [
            "Detailed explanation",
            "Practical examples",
            "Dependencies or related components"
        ]
        follow_up = (
            f"Can you explain the {domain} area step by step "
            "and provide a practical example?"
        )

    elif word_count < 35:
        completeness = 45
        severity = "Medium"
        gap_summary = (
            "The answer contains some information, but more detail "
            "is required before the knowledge can be transferred."
        )
        missing = [
            "Implementation details",
            "Potential problems",
            "Practical workflow"
        ]
        follow_up = (
            f"What are the important implementation details, "
            f"dependencies, and common issues related to {domain}?"
        )

    else:
        completeness = 70
        severity = "Low"
        gap_summary = (
            "The answer contains useful information. "
            "It should still be verified against project evidence."
        )
        missing = [
            "Verify the explanation against project documentation",
            "Confirm that another team member can follow the process"
        ]
        follow_up = (
            f"Can you describe a real example or situation involving "
            f"{domain} and explain how it was handled?"
        )

    return {
        "completeness": completeness,
        "severity": severity,
        "gap_summary": gap_summary,
        "missing_information": missing,
        "follow_up": follow_up,
        "reason": "Rule-based fallback evaluation based on answer length.",
        "status": "Needs review"
    }


# ============================================================
# AI KNOWLEDGE GAP ANALYSIS
# ============================================================

def analyze_answer(project, domain, question, answer):

    prompt = f"""
You are an AI-powered project knowledge transfer analyst.

Your task is to evaluate an outgoing employee's answer
during a technical handover interview.

PROJECT: {project}

KNOWLEDGE AREA: {domain}

KNOWLEDGE EXPECTED:
{KNOWLEDGE_AREAS[domain]}

INTERVIEW QUESTION:
{question}

EMPLOYEE ANSWER:
{answer}

Evaluate the answer using these rules:

1. Identify missing, incomplete, unclear or undocumented knowledge.
2. Check whether the answer explains the topic sufficiently.
3. Identify information that a successor would need to maintain the project.
4. Generate ONE specific follow-up question based on the actual answer.
5. Do not generate generic questions.
6. Do not assume information that is not present in the answer.
7. Assign severity:
   High: Critical knowledge is missing or the answer is unusable.
   Medium: Some important information is missing or unclear.
   Low: The answer is mostly complete but needs verification.
8. Give a completeness score between 0 and 100.
9. Treat an answer as needing evidence verification even if it sounds complete.

Return ONLY valid JSON in this exact structure:

{{
    "completeness": 65,
    "severity": "Medium",
    "gap_summary": "Explanation of the identified knowledge gap",
    "missing_information": [
        "Missing information 1",
        "Missing information 2"
    ],
    "follow_up": "One specific follow-up question",
    "reason": "Why this severity was assigned",
    "status": "Needs review"
}}
"""

    try:
        response = call_gemini(prompt)
        data = extract_json(response)
        result = normalize_result(data)
        result["evaluation_mode"] = "Gemini AI"
        return result

    except Exception as error:
        result = fallback_evaluation(answer, domain)
        result["evaluation_mode"] = "Rule-based fallback"
        result["error"] = str(error)
        return result


# ============================================================
# INITIAL INTERVIEW QUESTIONS
# ============================================================

def get_initial_question(domain):
    return KNOWLEDGE_AREAS[domain]


# ============================================================
# DISPLAY HELPERS
# ============================================================

def display_severity(severity):

    if severity == "High":
        st.error("HIGH PRIORITY GAP")

    elif severity == "Medium":
        st.warning("MEDIUM PRIORITY GAP")

    else:
        st.success("LOW PRIORITY GAP")


def display_analysis(result):

    st.subheader("Knowledge Analysis")

    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            "Knowledge Completeness",
            f'{result["completeness"]}%'
        )

    with col2:
        st.metric(
            "Gap Severity",
            result["severity"]
        )

    st.progress(result["completeness"] / 100)

    display_severity(result["severity"])

    st.markdown("**Identified Gap**")
    st.write(result["gap_summary"])

    st.markdown("**Missing or Unverified Information**")

    missing = result.get("missing_information", [])

    if missing:
        for item in missing:
            st.markdown(f"- {item}")
    else:
        st.write("No specific missing information was identified.")

    st.markdown("**Why was this priority assigned?**")
    st.write(result["reason"])

    st.markdown("**Recommended Follow-up Question**")

    st.info(result["follow_up"])

    st.caption(
        f'Evaluation method: {result["evaluation_mode"]}'
    )

    if result.get("error"):
        st.warning(
            "Gemini was unavailable. This result uses rule-based "
            "evaluation and should not be presented as an AI assessment."
        )


# ============================================================
# GAP DASHBOARD
# ============================================================

def render_gap_dashboard(project):

    st.subheader("Knowledge Gap Dashboard")

    records = get_all_gaps(project)

    if not records:
        st.info("No interview records found for this project yet.")
        return

    total = len(records)

    high = sum(1 for r in records if r["severity"] == "High")
    medium = sum(1 for r in records if r["severity"] == "Medium")
    low = sum(1 for r in records if r["severity"] == "Low")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total Assessments", total)
    col2.metric("High Priority", high)
    col3.metric("Medium Priority", medium)
    col4.metric("Low Priority", low)

    st.divider()

    st.markdown("### Identified Knowledge Gaps")

    for record in records:

        title = (
            f'{record["knowledge_area"]} | '
            f'{record["severity"]} Priority | '
            f'{record["created_at"]}'
        )

        with st.expander(title):

            st.write("**Contributor:**", record["contributor"])
            st.write("**Interview Question:**", record["question"])
            st.write("**Answer:**", record["answer"])

            st.write(
                "**Completeness:**",
                f'{record["completeness"]}%'
            )

            st.write("**Gap:**", record["gap_summary"])

            st.write("**Suggested Follow-up:**", record["follow_up"])

            st.write("**Current Status:**", record["status"])

            if record["status"] != "Resolved":

                if st.button(
                    "Mark as Resolved",
                    key=f'resolve_{record["id"]}'
                ):
                    update_gap_status(record["id"], "Resolved")
                    st.rerun()

            else:
                st.success("This gap has been marked as resolved.")


# ============================================================
# MAIN STREAMLIT FEATURE
# Import and call this function from app.py
# ============================================================

def render_knowledge_gap_detection():

    initialize_database()

    st.title("AI-Powered Knowledge Gap Detection")

    st.write(
        "Conduct structured knowledge interviews, identify missing "
        "project information, and generate targeted follow-up questions."
    )

    st.divider()

    # Project information

    st.subheader("Interview Details")

    project = st.text_input(
        "Project Name",
        placeholder="Enter project name"
    )

    contributor = st.text_input(
        "Outgoing Contributor",
        placeholder="Enter contributor name"
    )

    domain = st.selectbox(
        "Knowledge Area",
        list(KNOWLEDGE_AREAS.keys())
    )

    st.divider()

    # Interview section

    st.subheader("Knowledge Interview")

    question = get_initial_question(domain)

    st.markdown("**Interview Question**")
    st.info(question)

    answer = st.text_area(
        "Contributor's Answer",
        height=180,
        placeholder="Enter the contributor's explanation here..."
    )

    analyze_button = st.button(
        "Analyze Answer & Detect Gaps",
        type="primary",
        use_container_width=True
    )

    if analyze_button:

        if not project.strip():
            st.error("Please enter a project name.")

        elif not contributor.strip():
            st.error("Please enter the contributor's name.")

        elif not answer.strip():
            st.error("Please enter an interview answer.")

        else:

            with st.spinner(
                "Analyzing the answer and identifying knowledge gaps..."
            ):

                result = analyze_answer(
                    project,
                    domain,
                    question,
                    answer
                )

                save_analysis(
                    project,
                    contributor,
                    domain,
                    question,
                    answer,
                    result
                )

                st.session_state["improvement2_last_result"] = result

    # Latest analysis

    if "improvement2_last_result" in st.session_state:

        st.divider()

        display_analysis(
            st.session_state["improvement2_last_result"]
        )

    # Project dashboard

    st.divider()

    if project.strip():
        render_gap_dashboard(project.strip())
    else:
        st.caption(
            "Enter a project name above to view its saved knowledge gaps."
        )


# ============================================================
# OPTIONAL: RUN THIS FILE DIRECTLY FOR TESTING
# ============================================================

if __name__ == "__main__":
    render_knowledge_gap_detection()
