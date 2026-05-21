"""
Textual TUI for LongProbe Golden Sets.
"""

import contextlib
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import (
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    Select,
    TextArea,
)

from longprobe.core.golden import GoldenQuestion, GoldenSet


class QuestionItem(ListItem):
    """A list item representing a golden question."""

    def __init__(self, question: GoldenQuestion) -> None:
        super().__init__()
        self.question = question

    def compose(self) -> ComposeResult:
        text = self.question.question
        if len(text) > 40:
            text = text[:37] + "..."
        yield Label(f"[{self.question.id}] {text}")


class EditorApp(App):
    """Textual TUI for editing golden sets."""

    CSS = """
    Screen {
        layout: horizontal;
    }

    #left-pane {
        width: 35%;
        border-right: solid green;
    }

    #right-pane {
        width: 65%;
        padding: 1 2;
    }

    ListView {
        height: 100%;
    }

    .field-label {
        text-style: bold;
        color: cyan;
        margin-top: 1;
        margin-bottom: 1;
    }

    Input {
        margin-bottom: 1;
    }

    Select {
        margin-bottom: 1;
    }

    TextArea {
        height: 5;
        margin-bottom: 1;
    }
    """

    BINDINGS = [
        Binding("ctrl+s", "save", "Save", show=True),
        Binding("ctrl+n", "new_question", "New", show=True),
        Binding("ctrl+d", "delete_question", "Delete", show=True),
        Binding("q", "quit", "Quit", show=True),
    ]

    def __init__(self, golden_set: GoldenSet, file_path: str):
        super().__init__()
        self.golden_set = golden_set
        self.file_path = file_path
        self.current_question: GoldenQuestion | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(id="left-pane"):
                yield ListView(id="question-list")
            with Vertical(id="right-pane"):
                yield Label("ID", classes="field-label")
                yield Input(id="input-id", disabled=True)

                yield Label("Question", classes="field-label")
                yield Input(id="input-question")

                yield Label("Match Mode", classes="field-label")
                yield Select(
                    [("text", "text"), ("id", "id"), ("semantic", "semantic")],
                    id="select-match-mode",
                )

                yield Label("Required Chunks (one per line)", classes="field-label")
                yield TextArea(id="text-required-chunks")

                yield Label("Top K", classes="field-label")
                yield Input(id="input-top-k", type="integer")

                yield Label("Tags (comma separated)", classes="field-label")
                yield Input(id="input-tags")

        yield Footer()

    def on_mount(self) -> None:
        self.title = f"LongProbe Edit — {Path(self.file_path).name}"
        self.populate_list()

    def populate_list(self) -> None:
        list_view = self.query_one("#question-list", ListView)
        list_view.clear()
        for q in self.golden_set.questions:
            list_view.append(QuestionItem(q))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        item = event.item
        if isinstance(item, QuestionItem):
            self.load_question(item.question)

    def load_question(self, q: GoldenQuestion) -> None:
        self.current_question = q

        self.query_one("#input-id", Input).value = q.id
        self.query_one("#input-question", Input).value = q.question
        self.query_one("#select-match-mode", Select).value = q.match_mode
        self.query_one("#text-required-chunks", TextArea).text = "\n".join(
            q.required_chunks
        )
        self.query_one("#input-top-k", Input).value = str(q.top_k)
        self.query_one("#input-tags", Input).value = ", ".join(q.tags)

    def save_current_state(self) -> None:
        if not self.current_question:
            return

        q = self.current_question
        q.question = self.query_one("#input-question", Input).value

        match_mode = self.query_one("#select-match-mode", Select).value
        if match_mode:
            q.match_mode = str(match_mode)

        chunks_text = self.query_one("#text-required-chunks", TextArea).text
        q.required_chunks = [
            c.strip() for c in chunks_text.splitlines() if c.strip()
        ]

        with contextlib.suppress(ValueError):
            q.top_k = int(self.query_one("#input-top-k", Input).value)

        tags_text = self.query_one("#input-tags", Input).value
        q.tags = [t.strip() for t in tags_text.split(",") if t.strip()]

    def action_save(self) -> None:
        self.save_current_state()
        self.golden_set.to_yaml(self.file_path)
        self.notify(
            "Golden set saved successfully!",
            title="Saved",
            severity="information",
        )

    def action_new_question(self) -> None:
        import time

        self.save_current_state()
        new_id = f"q_{int(time.time())}"
        new_q = GoldenQuestion(
            id=new_id,
            question="New question...",
            match_mode="text",
            required_chunks=["chunk..."],
            top_k=5,
            tags=[],
        )
        self.golden_set.questions.append(new_q)
        self.populate_list()

        list_view = self.query_one("#question-list", ListView)
        list_view.index = len(self.golden_set.questions) - 1

    def action_delete_question(self) -> None:
        if not self.current_question:
            return

        self.golden_set.questions = [
            q
            for q in self.golden_set.questions
            if q.id != self.current_question.id
        ]
        self.current_question = None
        self.populate_list()
        self.notify("Question deleted", severity="warning")
