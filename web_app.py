"""Streamlit entry point. Run: python -m streamlit run web_app.py"""
import streamlit as st
from assistant.config import PROJECT_ROOT, load_config
from assistant.documents import DocumentCollection
from assistant.generator import OpenAIGenerator
from assistant.loader import load_passages
from assistant.presentation import describe_source
from assistant.search import search
from assistant.service import AssistantService


def render_message(message):
    with st.chat_message(message["role"]):
        # Plain text prevents document/model content from injecting links or HTML.
        st.text(message["text"])
        if message.get("error"):
            st.error(message["error"])
        for source in message.get("sources", []):
            with st.expander(f"Source {source.identifier}"):
                st.text(describe_source(source))
                st.text(source.passage.text)


def main():
    st.set_page_config(page_title="Local Knowledge Assistant", page_icon="📚")
    st.title("Local Knowledge Assistant")
    st.caption("Ask questions grounded in your local documents. Chat turns are independent questions.")
    config = load_config()
    collection = DocumentCollection(PROJECT_ROOT / "data/uploads")
    st.session_state.setdefault("messages", [])
    with st.sidebar:
        st.header("Knowledge collection")
        search_only = st.toggle("Search only (no API key needed)", value=True)
        include_samples = st.checkbox("Include fictional sample SOPs", value=True)
        st.caption("Uploads persist on disk and are shared by local browser sessions. Maximum 20 MB per file.")
        uploads = st.file_uploader("Upload documents", type=["md", "pdf", "docx"],
                                   accept_multiple_files=True)
        if st.button("Add uploaded documents", disabled=not uploads):
            changed = False
            for upload in uploads:
                try:
                    collection.add(upload.name, upload.getvalue())
                    st.success(f"Added {upload.name}")
                    changed = True
                except ValueError as error:
                    st.error(str(error))
                except OSError:
                    st.error("Could not save the document. Check local folder permissions.")
            if changed:
                st.session_state.messages = []
        st.subheader("Uploaded documents")
        documents = collection.list_documents()
        if not documents:
            st.caption("No uploaded documents yet.")
        for path in documents:
            st.text(path.name)
            if st.button("Remove", key=f"remove:{path.name}"):
                try:
                    collection.remove(path.name)
                    st.session_state.messages = []
                    st.rerun()
                except (ValueError, OSError):
                    st.error("Could not remove the document. Refresh and check folder permissions.")
        if include_samples:
            st.subheader("Fictional sample documents")
            for path in sorted(config.sop_dir.glob("*.md")):
                st.text(path.name)
            st.caption("Uncheck the sample option to exclude these documents.")
        if st.button("Clear chat"):
            st.session_state.messages = []

    passages, errors = collection.load()
    for name, error in errors:
        st.error(f"Cannot load {name}: {error}")
    if include_samples:
        try:
            passages.extend(load_passages(config.sop_dir))
        except (ValueError, OSError):
            st.error("Sample SOPs could not be loaded. Check SOP_DIR and document encoding.")
    if not search_only and not config.api_key:
        st.warning("AI answers require OPENAI_API_KEY in your local .env file. Search-only works without a key.")
    if not passages:
        st.info("No readable documents are loaded. Upload a document or enable the samples.")
    for message in st.session_state.messages:
        render_message(message)
    question = st.chat_input("Ask a question about the loaded documents")
    if question and question.strip():
        user_message = {"role": "user", "text": question}
        st.session_state.messages.append(user_message)
        render_message(user_message)
        message = {"role": "assistant", "text": "", "sources": []}
        if not search_only and not config.api_key:
            message["error"] = "API key is missing. Configure OPENAI_API_KEY or enable search-only."
        else:
            try:
                with st.spinner("Searching documents..."):
                    if search_only:
                        sources = search(question, passages, config.top_k)
                        message["text"] = ("Relevant passages are shown below." if sources
                                           else "No relevant evidence was found in the loaded documents.")
                        message["sources"] = sources
                    else:
                        generator = OpenAIGenerator(config.api_key, config.model)
                        answer = AssistantService(passages, generator, config.top_k).answer_question(question)
                        message["text"], message["sources"] = answer.text, answer.sources
            except Exception:
                # Do not display raw exceptions: SDK errors may contain request data.
                message["error"] = "Answer generation failed. Check the API key, model access, connectivity, and installed dependencies."
        st.session_state.messages.append(message)
        render_message(message)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        st.error("The application could not load its local collection. Check folder permissions and installed dependencies.")
