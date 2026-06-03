import streamlit as st
import json
import os
import re
import datetime as dt
from zoneinfo import ZoneInfo
from letters_project.orchestrator import Orchestrator
from letters_project.scheduler import Scheduler

st.set_page_config(page_title="Letters to My Future Self", page_icon="✉️", layout="wide")

# Common timezones for the dropdown
TIMEZONES = [
    "US/Eastern",
    "US/Central",
    "US/Mountain",
    "US/Pacific",
    "US/Hawaii",
    "Europe/London",
    "Europe/Paris",
    "Europe/Berlin",
    "Asia/Kolkata",
    "Asia/Tokyo",
    "Asia/Shanghai",
    "Asia/Dubai",
    "Australia/Sydney",
    "Pacific/Auckland",
    "UTC",
]

@st.cache_resource
def get_orchestrator() -> Orchestrator:
    # Streamlit Cloud has a read-only source directory;
    # use /tmp for the database so writes succeed.
    import tempfile
    db_path = os.path.join(tempfile.gettempdir(), "letters.db")
    return Orchestrator(db_path=db_path)

@st.cache_resource
def get_scheduler(_orch: Orchestrator) -> Scheduler:
    return Scheduler(_orch, interval=30)

def main() -> None:
    st.title("✉️ Letters to My Future Self")

    orch = get_orchestrator()
    scheduler = get_scheduler(orch)

    # --- Authentication ---
    # On Streamlit Cloud with OAuth configured: use Google login
    # Locally without OAuth: fall back to manual email input
    try:
        is_logged_in = st.experimental_user.is_logged_in
    except AttributeError:
        is_logged_in = False

    if not is_logged_in:
        # Check if auth is configured by trying to detect secrets
        try:
            auth_configured = bool(st.secrets.get("auth"))
        except Exception:
            auth_configured = False

        if auth_configured:
            # OAuth is set up but user hasn't logged in — redirect immediately
            st.login("google")
            st.stop()

    # --- Sidebar ---
    with st.sidebar:
        if is_logged_in:
            user_email = st.experimental_user.email.strip().lower()
            st.markdown(f"### 👤 {getattr(st.experimental_user, 'name', user_email)}")
            st.caption(user_email)
            if st.button("Log out"):
                st.logout()
        else:
            # Local dev fallback — manual email input
            st.markdown("### 👤 Your identity")
            user_email = st.text_input(
                "Your email",
                value="",
                placeholder="you@example.com",
                help="Letters and sent emails are filtered to this address.",
            ).strip().lower()
            if not user_email:
                st.info("Enter your email to see your letters.")

        st.markdown("### 🕐 Timezone")
        user_tz_name = st.selectbox(
            "Your timezone",
            TIMEZONES,
            index=TIMEZONES.index("US/Central"),
            help="Times are shown and saved in your selected timezone.",
            label_visibility="collapsed",
        )
        user_tz = ZoneInfo(user_tz_name)

        st.markdown("---")
        if scheduler.running:
            st.caption("🟢 Scheduler active — checking for deliveries every 30s")
        else:
            st.caption("🔴 Scheduler stopped")

    tab1, tab2, tab3 = st.tabs(["Create", "Letters", "Sent Emails"])

    # ---------- TAB 1: CREATE ----------
    with tab1:
        st.subheader("Compose a new letter")
        content = st.text_area("Letter content", height=200,
                               placeholder="Dear future me…")

        st.caption("When should this letter be delivered?")
        col1, col2 = st.columns(2)

        now = dt.datetime.now(user_tz)

        # Calculate next valid 15-min slot (only once, so it won't reset user edits)
        if "init_release_time_str" not in st.session_state:
            remainder = now.minute % 15
            next_slot = now.replace(second=0, microsecond=0) + dt.timedelta(minutes=15 - remainder)
            st.session_state.init_release_time_str = next_slot.strftime("%I:%M %p").lstrip("0")

        with col1:
            release_date = st.date_input(
                "Release date",
                value=now.date(),
                min_value=now.date(),
                help="Pick from the calendar or type a date directly (e.g. 2040/06/15).",
            )

        with col2:
            time_str = st.text_input(
                "Release time (12hr or 24hr)",
                value=st.session_state.init_release_time_str,
                placeholder="9:30 AM  or  14:30",
                help="Both formats work: **12-hour** (9:30 AM, 2:45 PM) and **24-hour** (14:30, 21:59).",
            )

            # Parse the time string
            release_time = None
            if time_str.strip():
                raw = time_str.strip()
                for fmt in ("%I:%M %p", "%I:%M%p", "%H:%M"):
                    try:
                        release_time = dt.datetime.strptime(raw, fmt).time()
                        break
                    except ValueError:
                        continue
                if release_time is None:
                    st.warning("⚠️ Could not parse time. Try formats like 9:30 AM or 14:30.")

        to_address = st.text_input("Recipient email",
                                   value=user_email if user_email else "",
                                   placeholder="recipient@example.com")

        # --- Validation ---
        validation_message = None
        has_content = bool(content.strip())
        email_raw = to_address.strip()
        has_email = bool(email_raw)

        # Validate email format
        if has_email and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email_raw):
            validation_message = "Please enter a valid email address."

        # Combine date + time and check if it's in the past
        release_dt = None
        if release_date and release_time and validation_message is None:
            # Attach user's timezone so comparison with now (tz-aware) works
            release_dt = dt.datetime.combine(release_date, release_time, tzinfo=user_tz)
            if release_dt <= now:
                validation_message = "The selected date and time is in the past. Please pick a future time."

        # Missing content
        if not has_content and validation_message is None:
            validation_message = "Write something in your letter before sending!"

        # Missing email
        if not has_email and validation_message is None:
            validation_message = "Please enter a recipient email address."

        # Show warning
        if validation_message:
            st.warning(f"⚠️ {validation_message}")

        can_create = (
            has_content
            and has_email
            and release_dt is not None
            and validation_message is None
        )

        if st.button("Create", type="primary", disabled=not can_create):
            # Convert to UTC for storage (ChronoAgent compares against UTC)
            release_utc = release_dt.astimezone(ZoneInfo("UTC"))
            date_iso = release_utc.strftime("%Y-%m-%dT%H:%M:%S")
            letter_id = orch.create_letter(
                content.strip(),
                date_iso,
                email_raw,
            )
            st.success(
                f"Letter **#{letter_id}** created! It will be delivered to "
                f"**{email_raw}** on **{release_dt.strftime('%b %d, %Y at %I:%M %p')} ({user_tz_name})**."
            )
    


    # ---------- TAB 2: LETTERS ----------
    with tab2:
        st.subheader("Your letters")

        if not user_email:
            st.warning("Please enter your email in the sidebar to view your letters.")
        else:
            all_letters = orch.db.list_letters()
            letters = [l for l in all_letters
                       if (l.get("to_address") or "").strip().lower() == user_email]

            if not letters:
                st.info("No letters found for your email. Create one in the **Create** tab!")
            else:
                # --- Status emoji mapping ---
                _status_icon = {
                    "draft": "📝",
                    "sealed": "🔒",
                    "scheduled": "📅",
                    "ready": "🚀",
                    "delivered": "📬",
                    "archived": "🗂️",
                }

                # --- Build a clean, user-friendly table ---
                display_rows = []
                for row in letters:
                    # Truncate content for preview
                    raw_content = row.get("content") or ""
                    preview = (raw_content[:60] + "…") if len(raw_content) > 60 else raw_content

                    # Format release date for readability
                    raw_date = row.get("release_date") or ""
                    try:
                        parsed_dt = dt.datetime.fromisoformat(raw_date)
                        friendly_date = parsed_dt.strftime("%b %d, %Y  %I:%M %p")
                    except (ValueError, TypeError):
                        friendly_date = raw_date if raw_date else "—"

                    status = row.get("status") or "unknown"
                    icon = _status_icon.get(status, "❓")

                    display_rows.append({
                        "ID": row.get("id"),
                        "Status": f"{icon} {status.capitalize()}",
                        "To": row.get("to_address") or "—",
                        "Preview": preview,
                        "Release Date": friendly_date,
                    })

                st.dataframe(display_rows, use_container_width=True, hide_index=True)

                # --- Detail viewer ---
                st.markdown("---")
                ids = [row["id"] for row in letters if "id" in row]
                if not ids:
                    st.warning("No valid letter IDs found.")
                else:
                    selected_id = st.selectbox("View letter details", ids,
                                               format_func=lambda x: f"Letter #{x}")

                    if st.button("Load details"):
                        try:
                            letter = orch.db.get_letter(int(selected_id))
                        except KeyError:
                            st.error(f"Letter #{selected_id} not found. It may have been deleted.")
                        else:
                            status = letter.get("status") or "unknown"
                            icon = _status_icon.get(status, "❓")

                            st.markdown(f"**Status:** {icon} {status.capitalize()}")
                            st.markdown(f"**To:** {letter.get('to_address') or '—'}")

                            # Format release date
                            raw_date = letter.get("release_date") or ""
                            try:
                                parsed_dt = dt.datetime.fromisoformat(raw_date)
                                st.markdown(f"**Release date:** {parsed_dt.strftime('%b %d, %Y  %I:%M %p')}")
                            except (ValueError, TypeError):
                                st.markdown(f"**Release date:** {raw_date if raw_date else '—'}")

                            # Show content (read-only)
                            st.markdown("**Content:**")
                            st.code(letter.get("content") or "(empty)", language="text")

                            # Show summary only if available
                            summary = letter.get("summary")
                            if summary:
                                st.markdown(f"**Summary:** {summary}")

    # ---------- TAB 3: SENT EMAILS ----------
    with tab3:
        st.subheader("Sent emails (mock log)")

        if not user_email:
            st.warning("Please enter your email in the sidebar to view sent emails.")
        else:
            log_path = os.environ.get("MOCK_EMAIL_LOG", "mock_emails.jsonl")
            if not os.path.exists(log_path):
                st.info("No emails have been sent yet.")
            else:
                all_rows = []
                with open(log_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            if line.startswith("{") and "'" in line and '"' not in line:
                                line_json = line.replace("'", '"')
                                all_rows.append(json.loads(line_json))
                            else:
                                all_rows.append(json.loads(line))
                        except Exception:
                            all_rows.append({"raw": line})

                # Filter to only this user's emails
                rows = [r for r in all_rows
                        if (r.get("to") or "").strip().lower() == user_email]

                if not rows:
                    st.info("No sent emails found for your address.")
                else:
                    st.write(f"Total sent to you: {len(rows)}")
                    st.dataframe(rows, use_container_width=True)

                    st.markdown("### Preview last email")
                    last = rows[-1]
                    st.write("**To:**", last.get("to"))
                    st.write("**Subject:**", last.get("subject"))
                    st.code(last.get("body", ""), language="text")

if __name__ == "__main__":
    main()