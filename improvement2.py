
import streamlit as st
import sqlite3
import re
import os
from datetime import datetime

# ==========================================================
# DEVHANDOVER AI
# IMPROVEMENT 2: KNOWLEDGE GAP DETECTION
# API-FREE RULE-BASED IMPLEMENTATION
# ==========================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "knowledge_gaps.db")


# ==========================================================
# 1. KNOWLEDGE AREAS AND EXPECTED INFORMATION
# ==========================================================

KNOWLEDGE_AREAS = {
    "Architecture": {
        "description": "System architecture and component structure",
        "checks": {
            "components": ["component", "module", "service", "layer"],
            "communication": ["communicate", "interaction", "connect", "flow"],
            "structure": ["architecture", "structure", "design", "system"],
            "dependencies": ["dependency", "dependencies", "dependent"],
            "purpose": ["purpose", "responsibility", "function", "role"]
        }
    },

    "Database": {
        "description": "Database structure and data management",
        "checks": {
            "tables": ["table", "tables", "collection", "schema"],
            "relationships": ["relationship", "foreign key", "primary key", "relation"],
            "queries": ["query", "queries", "sql", "retrieval"],
            "backup": ["backup", "restore", "recovery"],
            "data_flow": ["data flow", "insert", "update", "storage"]
        }
    },

    "APIs and Integrations": {
        "description": "APIs and external integrations",
        "checks": {
            "endpoints": ["endpoint", "route", "url", "api"],
            "requests": ["request", "response", "payload", "json"],
            "authentication": ["authentication", "token", "authorization", "api key"],
            "errors": ["error handling", "exception", "status code", "validation"],
            "integration": ["integration", "third party", "external service"]
        }
    },

    "Deployment": {
        "description": "Application deployment and maintenance",
        "checks": {
            "platform": ["server", "cloud", "hosting", "platform"],
            "process": ["deploy", "deployment", "release", "publish"],
            "configuration": ["configuration", "config", "environment", "variable"],
            "monitoring": ["monitor", "logs", "logging", "monitoring"],
            "rollback": ["rollback", "revert", "previous version", "recovery"]
        }
    },

    "Security": {
        "description": "Security and access management",
        "checks": {
            "authentication": ["authentication", "login", "sign in", "password"],
            "authorization": ["authorization", "permissions", "access control", "roles"],
            "encryption": ["encryption", "encrypted", "hashing", "hash"],
            "data_protection": ["sensitive data", "privacy", "data protection", "confidential"],
            "validation": ["validation", "input validation", "sanitization"]
        }
    },

    "Debugging and Troubleshooting": {
        "description": "Debugging and problem resolution",
        "checks": {
            "errors": ["error", "exception", "failure", "bug"],
            "logs": ["logs", "logging", "console", "traceback"],
            "diagnosis": ["debug", "diagnose", "identify", "investigate"],
            "solution": ["solution", "fix", "resolve", "correct"],
            "prevention": ["prevent", "prevention", "monitor", "testing"]
        }
    },

    "Business Logic": {
        "description": "Core application workflows and business rules",
        "checks": {
            "workflow": ["workflow", "process", "steps", "flow"],
            "rules": ["rule", "rules", "condition", "logic"],
            "input_output": ["input", "output", "result", "response"],
            "edge_cases": ["edge case", "exception", "special case", "invalid"],
            "decisions": ["decision", "reason", "because", "approach"]
        }
    },

    "Dependencies": {
        "description": "Libraries, packages and external dependencies",
        "checks": {
            "libraries": ["library", "libraries", "package", "packages"],
            "versions": ["version", "versions", "upgrade", "compatibility"],
            "installation": ["install", "installation", "requirements", "setup"],
            "external": ["external", "third party", "service", "integration"],
            "failure": ["failure", "unavailable", "fallback", "alternative"]
        }
    },

    "Testing": {
        "description": "Testing strategy and quality assurance",
        "checks": {
            "test_cases": ["test case", "test cases", "scenario", "cases"],
            "unit_testing": ["unit test", "unit testing", "function testing"],
            "integration": ["integration test", "integration testing"],
            "validation": ["validation", "expected result", "actual result"],
            "limitations": ["limitation", "limitations", "known issue", "coverage"]
        }
    },

    "Other": {
        "description": "Other important project knowledge",
        "checks": {
            "purpose": ["purpose", "objective", "goal"],
            "process": ["process", "workflow", "procedure"],
            "implementation": ["implementation", "implemented", "developed"],
            "problems": ["problem", "challenge", "issue"],
            "solution": ["solution", "resolved", "improvement"]
        }
    }
}


# ==========================================================
# 2. DATABASE FUNCTIONS
# ==========================================================

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database():

    conn = get_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_gaps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_name TEXT NOT NULL,
            contributor TEXT NOT NULL,
            knowledge_area TEXT NOT NULL,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            completeness INTEGER NOT NULL,
            severity TEXT NOT NULL,
            gap_summary TEXT,
            missing_information TEXT,
            follow_up TEXT,
            status TEXT DEFAULT 'Open',
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


def save_analysis(project, contributor, domain, question, answer, result):

    conn = get_connection()

    conn.execute("""
        INSERT INTO knowledge_gaps (
            project_name,
            contributor,
            knowledge_area,
            question,
            answer,
            completeness,
            severity,
            gap_summary,
            missing_information,
            follow_up,
            status,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        project,
        contributor,
        domain,
        question,
        answer,
        result["completeness"],
        result["severity"],
        result["gap_summary"],
        "\n".join(result["missing_information"]),
        result["follow_up"],
        "Open",
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()


def get_all_gaps(project=None):

    conn = get_connection()

    if project:
        records = conn.execute("""
            SELECT * FROM knowledge_gaps
            WHERE project_name = ?
            ORDER BY created_at DESC
        """, (project,)).fetchall()

    else:
        records = conn.execute("""
            SELECT * FROM knowledge_gaps
            ORDER BY created_at DESC
        """).fetchall()

    conn.close()

    return [dict(record) for record in records]


def update_gap_status(gap_id, status):

    conn = get_connection()

    conn.execute("""
        UPDATE knowledge_gaps
        SET status = ?
        WHERE id = ?
    """, (status, gap_id))

    conn.commit()
    conn.close()


# ==========================================================
# 3. TEXT PROCESSING
# ==========================================================

def normalize_text(text):

    text = text.lower()

    text = re.sub(r"[^a-z0-9\s_-]", " ", text)

    text = re.sub(r"\s+", " ", text)

    return text.strip()


def contains_keyword(text, keyword):

    text = normalize_text(text)
    keyword = normalize_text(keyword)

    pattern = r"(?<![a-z0-9])" + re.escape(keyword) + r"(?![a-z0-9])"

    return bool(re.search(pattern, text))


# ==========================================================
# 4. FOLLOW-UP QUESTION GENERATION
# ==========================================================

FOLLOW_UP_TEMPLATES = {
    "components": "Can you explain the main components and their individual responsibilities?",
    "communication": "How do these components communicate with each other?",
    "structure": "Can you explain the overall structure and design of this system?",
    "dependencies": "What are the important dependencies, and how do they affect this area?",
    "purpose": "Why was this approach selected, and what purpose does it serve?",

    "tables": "Can you describe the important database tables or collections?",
    "relationships": "How are the database tables related to each other?",
    "queries": "What important queries are used to retrieve or modify the data?",
    "backup": "How is the database backed up and restored?",
    "data_flow": "How does data move through the application and reach the database?",

    "endpoints": "What are the important API endpoints and what does each endpoint do?",
    "requests": "What request and response formats are used?",
    "authentication": "How are API requests authenticated and authorized?",
    "errors": "How are API errors and invalid requests handled?",
    "integration": "Which external services are integrated and how do they work?",

    "platform": "Where is the application hosted and what infrastructure does it require?",
    "process": "Can you explain the deployment process step by step?",
    "configuration": "Which environment variables and configuration settings are required?",
    "monitoring": "How do you monitor the application and inspect its logs?",
    "rollback": "How can you roll back to a previous working version?",

    "encryption": "How is sensitive information protected?",
    "authorization": "How are user roles and permissions managed?",
    "data_protection": "How is confidential project data protected?",
    "validation": "How does the system validate user input?",

    "errors": "What are the common errors and how do you identify them?",
    "logs": "Where can someone find the logs needed for debugging?",
    "diagnosis": "What steps should a successor follow to diagnose a problem?",
    "solution": "Can you describe how a common issue was fixed?",
    "prevention": "What measures help prevent the same issue from happening again?",

    "workflow": "Can you explain the complete workflow step by step?",
    "rules": "What important business rules and conditions does the system follow?",
    "input_output": "What inputs does this process accept and what outputs does it produce?",
    "edge_cases": "What happens when the system receives invalid or unexpected input?",
    "decisions": "Why were these implementation decisions made?",

    "libraries": "Which important libraries and packages does the project use?",
    "versions": "Are there specific package versions or compatibility requirements?",
    "installation": "How can a new developer install and configure the dependencies?",
    "external": "Which external services does the project depend on?",
    "failure": "What happens if an external dependency becomes unavailable?",

    "test_cases": "What are the most important test cases for this area?",
    "unit_testing": "Which individual functions or modules have unit tests?",
    "integration": "How do you test interactions between different components?",
    "validation": "How do you verify that the actual result matches the expected result?",
    "limitations": "What testing limitations or known issues should the successor know about?",

    "implementation": "Can you explain how this functionality was implemented?",
    "problems": "What major problems or challenges were encountered?",
    "solution": "How were those challenges resolved?"
}


# ==========================================================
# 5. KNOWLEDGE GAP DETECTION ENGINE
# ==========================================================

def analyze_answer(domain, answer):

    answer = normalize_text(answer)

    config = KNOWLEDGE_AREAS[domain]

    checks = config["checks"]

    word_count = len(answer.split())

    matched = []
    missing = []

    # Check each expected knowledge topic.

    for check_name, keywords in checks.items():

        found = any(
            contains_keyword(answer, keyword)
            for keyword in keywords
        )

        if found:
            matched.append(check_name)
        else:
            missing.append(check_name)

    total_checks = len(checks)

    coverage = (len(matched) / total_checks) * 100

    # Answer detail score.

    if word_count >= 60:
        detail_score = 100

    elif word_count >= 35:
        detail_score = 80

    elif word_count >= 20:
        detail_score = 60

    elif word_count >= 10:
        detail_score = 35

    else:
        detail_score = 10

    # Overall completeness score.

    completeness = round(
        (coverage * 0.75) + (detail_score * 0.25)
    )

    # Identify severity.

    if completeness < 40:
        severity = "High"

    elif completeness < 70:
        severity = "Medium"

    else:
        severity = "Low"

    # Generate missing information list.

    missing_information = []

    for item in missing:

        if item in FOLLOW_UP_TEMPLATES:
            missing_information.append(
                FOLLOW_UP_TEMPLATES[item]
            )

    # Create targeted follow-up.

    if missing:

        follow_up = FOLLOW_UP_TEMPLATES.get(
            missing[0],
            "Can you provide more details about this topic?"
        )

    elif completeness < 80:

        follow_up = (
            "Can you provide a practical example and explain "
            "how a new team member would perform this task?"
        )

    else:

        follow_up = (
            "Can you describe a real project scenario involving "
            "this area and explain how it was handled?"
        )

    # Generate gap summary.

    if severity == "High":

        gap_summary = (
            f"Critical knowledge gaps were detected in {domain}. "
            f"Only {len(matched)} of {total_checks} expected knowledge "
            "topics were identified. More information is required "
            "before a successor can confidently take ownership."
        )

    elif severity == "Medium":

        gap_summary = (
            f"Some knowledge about {domain} is documented, but "
            "important details are still missing. A follow-up "
            "interview is recommended."
        )

    else:

        gap_summary = (
            f"The answer covers most expected topics in {domain}. "
            "The information should still be verified against "
            "project documentation or practical evidence."
        )

    return {
        "completeness": completeness,
        "severity": severity,
        "matched_topics": matched,
        "missing_topics": missing,
        "missing_information": missing_information,
        "gap_summary": gap_summary,
        "follow_up": follow_up,
        "word_count": word_count,
        "coverage": round(coverage)
    }


# ==========================================================
# 6. INITIAL INTERVIEW QUESTION
# ==========================================================

def get_initial_question(domain):

    return (
        f"You are explaining the {domain} area of the project "
        "to a new team member. "
        f"{KNOWLEDGE_AREAS[domain]['description']}. "
        "Explain how it works, its important components, "
        "and what a successor needs to know."
    )


# ==========================================================
# 7. DISPLAY ANALYSIS
# ==========================================================

def display_analysis(result):

    st.subheader("Knowledge Analysis")

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Completeness",
        f'{result["completeness"]}%'
    )

    col2.metric(
        "Severity",
        result["severity"]
    )

    col3.metric(
        "Topic Coverage",
        f'{result["coverage"]}%'
    )

    st.progress(result["completeness"] / 100)

    if result["severity"] == "High":

        st.error("HIGH PRIORITY: Critical knowledge gaps detected.")

    elif result["severity"] == "Medium":

        st.warning("MEDIUM PRIORITY: Additional information required.")

    else:

        st.success("LOW PRIORITY: Most expected topics were covered.")

    st.markdown("### Gap Summary")
    st.write(result["gap_summary"])

    st.markdown("### Topics Identified")

    if result["matched_topics"]:

        for topic in result["matched_topics"]:
            st.markdown(f"- {topic.replace('_', ' ').title()}")

    else:
        st.write("No expected topics were identified.")

    st.markdown("### Missing Knowledge")

    if result["missing_information"]:

        for item in result["missing_information"]:
            st.markdown(f"- {item}")

    else:

        st.success("All configured knowledge checks were matched.")

    st.markdown("### Recommended Follow-up Question")

    st.info(result["follow_up"])

    st.caption(
        f'Answer length: {result["word_count"]} words | '
        "Evaluation method: Rule-based analysis"
    )


# ==========================================================
# 8. KNOWLEDGE GAP DASHBOARD
# ==========================================================

def render_gap_dashboard(project):

    st.subheader("Knowledge Gap Dashboard")

    records = get_all_gaps(project)

    if not records:

        st.info("No interview records available for this project.")
        return

    total = len(records)

    high = sum(
        1 for record in records
        if record["severity"] == "High"
    )

    medium = sum(
        1 for record in records
        if record["severity"] == "Medium"
    )

    low = sum(
        1 for record in records
        if record["severity"] == "Low"
    )

    open_gaps = sum(
        1 for record in records
        if record["status"] == "Open"
    )

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total Assessments", total)
    col2.metric("High Priority", high)
    col3.metric("Medium Priority", medium)
    col4.metric("Open Gaps", open_gaps)

    st.divider()

    st.markdown("### Interview Records")

    for record in records:

        heading = (
            f'{record["knowledge_area"]} | '
            f'{record["severity"]} Priority | '
            f'ID: {record["id"]}'
        )

        with st.expander(heading):

            st.write("**Contributor:**", record["contributor"])

            st.write("**Interview Question:**")
            st.write(record["question"])

            st.write("**Contributor's Answer:**")
            st.write(record["answer"])

            st.write(
                "**Completeness:**",
                f'{record["completeness"]}%'
            )

            st.write("**Identified Gap:**")
            st.write(record["gap_summary"])

            st.write("**Missing Information:**")

            for item in record["missing_information"].split("\n"):

                if item.strip():
                    st.markdown(f"- {item}")

            st.write("**Suggested Follow-up:**")
            st.info(record["follow_up"])

            st.write("**Status:**", record["status"])

            if record["status"] == "Open":

                if st.button(
                    "Mark as Resolved",
                    key=f'resolve_{record["id"]}'
                ):

                    update_gap_status(record["id"], "Resolved")

                    st.rerun()

            else:

                st.success("This gap has been resolved.")


# ==========================================================
# 9. MAIN IMPROVEMENT 2 INTERFACE
# ==========================================================

def render_knowledge_gap_detection():

    initialize_database()

    st.title("AI-Powered Knowledge Gap Detection")

    st.write(
        "Identify missing project knowledge, evaluate interview "
        "answers, and generate targeted follow-up questions."
    )

    st.caption(
        "This version uses transparent rule-based analysis. "
        "It does not require an external AI API."
    )

    st.divider()

    # Interview details

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
        "Select Knowledge Area",
        list(KNOWLEDGE_AREAS.keys())
    )

    st.caption(KNOWLEDGE_AREAS[domain]["description"])

    st.divider()

    # Interview question

    st.subheader("Knowledge Interview")

    question = get_initial_question(domain)

    st.markdown("**Interview Question**")

    st.info(question)

    answer = st.text_area(
        "Contributor's Answer",
        height=180,
        placeholder=(
            "Enter the contributor's explanation here..."
        )
    )

    if st.button(
        "Analyze Answer & Detect Gaps",
        type="primary",
        use_container_width=True
    ):

        if not project.strip():

            st.error("Please enter a project name.")

        elif not contributor.strip():

            st.error("Please enter the contributor's name.")

        elif len(answer.strip()) < 5:

            st.error("Please enter a meaningful interview answer.")

        else:

            with st.spinner("Analyzing project knowledge..."):

                result = analyze_answer(domain, answer)

                save_analysis(
                    project.strip(),
                    contributor.strip(),
                    domain,
                    question,
                    answer.strip(),
                    result
                )

                st.session_state["improvement2_result"] = result

                st.session_state["improvement2_project"] = project.strip()

    # Display latest result

    if "improvement2_result" in st.session_state:

        st.divider()

        display_analysis(
            st.session_state["improvement2_result"]
        )

    # Display dashboard

    st.divider()

    st.subheader("Saved Knowledge Gap Records")

    if project.strip():

        render_gap_dashboard(project.strip())

    else:

        st.caption(
            "Enter a project name to view its saved interview records."
        )


# ==========================================================
# 10. RUN STANDALONE OR IMPORT INTO MAIN APP
# ==========================================================

if __name__ == "__main__":

    st.set_page_config(
        page_title="DevHandover AI - Knowledge Gap Detection",
        page_icon="🧠",
        layout="wide"
    )

    render_knowledge_gap_detection()
