"""Optional Streamlit UI for Letters to My Future Self.

The Streamlit application provides a simple web interface over the
command‑line orchestrator. It allows users to compose and schedule
letters, view their current status and manually trigger the Chrono
agent via a "Tick" button. This UI is optional and requires the
``streamlit`` package. If ``streamlit`` is not installed the app will
not run.
"""

from __future__ import annotations

try:
    import streamlit as st  # type: ignore
except ImportError:
    raise RuntimeError(
        "streamlit is not installed. Install it via pip to use the web UI."
    )

from ..orchestrator import Orchestrator


@st.cache_resource
def get_orchestrator() -> Orchestrator:
    # Use a single orchestrator instance across reruns
    return Orchestrator()


def main() -> None:
    st.title("Letters to My Future Self")
    orch = get_orchestrator()
    # Tabs for creating and listing letters
    tab1, tab2 = st.tabs(["Create Letter", "Manage Letters"])
    with tab1:
        st.subheader("Compose a new letter")
        content = st.text_area("Letter content", height=200)
        date = st.text_input(
            "Release date (ISO format)", value="2027-01-01T00:00:00"
        )
        to_address = st.text_input("Recipient email", value="user@example.com")
        if st.button("Create"):
            if not content or not date or not to_address:
                st.error("All fields are required")
            else:
                letter_id = orch.create_letter(content, date, to_address)
                st.success(f"Letter created with ID {letter_id}")
    with tab2:
        st.subheader("Current letters")
        letters = orch.list_letters()
        if not letters:
            st.info("No letters in the system.")
        else:
            for letter in letters:
                st.write(letter)
        if st.button("Tick"):
            orch.tick()
            st.success("System tick processed")


if __name__ == "__main__":
    main()