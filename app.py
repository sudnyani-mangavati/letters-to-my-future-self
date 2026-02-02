import streamlit as st
import json
import os
import datetime as dt
from letters_project.orchestrator import Orchestrator

st.set_page_config(page_title="Letters to My Future Self", page_icon="✉️", layout="wide")

@st.cache_resource
def get_orchestrator() -> Orchestrator:
    return Orchestrator()

def main() -> None:
    st.title("✉️ Letters to My Future Self")

    orch = get_orchestrator()
    tab1, tab2, tab3 = st.tabs(["Create", "Letters", "Sent Emails"])

    # ---------- TAB 1: CREATE ----------
    with tab1:
        st.subheader("Compose a new letter")
        content = st.text_area("Letter content", height=200)

        st.caption("Release date & time")
        col1, col2 = st.columns(2)

        now = dt.datetime.now()

        with col1:
            # blank input with placeholder only
            date_str = st.text_input(
                "Release date",
                value="",
                placeholder="MM/DD/YYYY",
            )

        with col2:
            # blank input with placeholder only
            time_str = st.text_input(
                "Release time",
                value="",
                placeholder="HH:MM AM/PM (e.g., 09:30 PM)",
            )

        to_address = st.text_input("Recipient email", value="su@example.com")

        # --- Parse + validate only if user typed something ---
        release_dt = None
        parse_error = None

        if date_str.strip() or time_str.strip():
            if not date_str.strip() or not time_str.strip():
                parse_error = "Enter both date and time."
            else:
                parsed = None
                # Try 12-hour format first: 09:30 PM
                try:
                    parsed = dt.datetime.strptime(
                        f"{date_str.strip()} {time_str.strip()}",
                        "%m/%d/%Y %I:%M %p",
                    )
                except ValueError:
                    # Fallback: 24-hour format: 21:30
                    try:
                        parsed = dt.datetime.strptime(
                            f"{date_str.strip()} {time_str.strip()}",
                            "%m/%d/%Y %H:%M",
                        )
                    except ValueError:
                        parse_error = "Invalid format. Use MM/DD/YYYY and HH:MM AM/PM (or 24h HH:MM)."

                release_dt = parsed

        is_past = False
        if release_dt and release_dt <= now:
            is_past = True

        if parse_error:
            st.warning(f"⚠️ {parse_error}")
        elif is_past:
            st.warning("⚠️ You can only select a future date and time.")

        if st.button("Create", type="primary"):
            if not content.strip() or not to_address.strip():
                st.error("All fields are required")
            elif not release_dt:
                st.error("Please enter a release date and time.")
            elif parse_error:
                st.error(parse_error)
            elif is_past:
                st.error("Release date & time must be in the future.")
            else:
                date_iso = release_dt.strftime("%Y-%m-%dT%H:%M:%S")
                letter_id = orch.create_letter(content.strip(), date_iso, to_address.strip())
                st.success(f"Letter created with ID {letter_id}")


    # ---------- TAB 2: LETTERS ----------
    with tab2:
        st.subheader("Current letters")

        letters = orch.db.list_letters()
        if not letters:
            st.info("No letters yet.")
        else:
            # Hide sensitive fields in table view
            safe_letters = []
            for row in letters:
                r = dict(row)
                r.pop("encryption_key", None)
                r.pop("encrypted_content", None)
                safe_letters.append(r)

            st.dataframe(safe_letters, use_container_width=True)

            st.markdown("### View a letter (safe fields only)")
            ids = [row["id"] for row in letters if "id" in row]
            selected_id = st.selectbox("Select letter ID", ids)

            if st.button("Load details"):
                letter = orch.db.get_letter(int(selected_id))
                safe = dict(letter)
                safe.pop("encryption_key", None)
                safe.pop("encrypted_content", None)
                st.json(safe)

    # ---------- TAB 3: SENT EMAILS ----------
    with tab3:
        st.subheader("Sent emails (mock log)")

        log_path = os.environ.get("MOCK_EMAIL_LOG", "mock_emails.jsonl")
        if not os.path.exists(log_path):
            st.info(f"No log found yet: {log_path}")
        else:
            rows = []
            with open(log_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        if line.startswith("{") and "'" in line and '"' not in line:
                            line_json = line.replace("'", '"')
                            rows.append(json.loads(line_json))
                        else:
                            rows.append(json.loads(line))
                    except Exception:
                        rows.append({"raw": line})

            st.write(f"Total sent: {len(rows)}")
            st.dataframe(rows, use_container_width=True)

            st.markdown("### Preview last email")
            if rows:
                last = rows[-1]
                st.write("**To:**", last.get("to"))
                st.write("**Subject:**", last.get("subject"))
                # NOT editable:
                st.code(last.get("body", ""), language="text")

if __name__ == "__main__":
    main()
