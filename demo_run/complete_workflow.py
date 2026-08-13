#!/usr/bin/env python3
"""
LongProbe — Complete Workflow Demo with Professional TUI
Shows the full RAG regression testing workflow with live updates
"""

import os
import shutil
import json
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler

from rich.console import Console, Group
from rich.panel import Panel
from rich.text import Text
from rich.live import Live
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

console = Console()

# ── Paths ──
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
GOLDENS_PATH = os.path.join(SCRIPT_DIR, "demo_goldens.yaml")
BASELINE_PATH = os.path.join(SCRIPT_DIR, ".demo_baselines")

# Clean up
if os.path.exists(BASELINE_PATH):
    shutil.rmtree(BASELINE_PATH)
if os.path.exists(GOLDENS_PATH):
    os.remove(GOLDENS_PATH)

# ═══════════════════════════════════════════════════════════════════════════
# Production-Grade Sample RAG API Engine
# ═══════════════════════════════════════════════════════════════════════════

DOCUMENTS = [
    {"chunk_id": "doc_refund",   "content": "The refund policy allows for full refunds within 30 days of purchase. No questions asked. After 30 days, a 15% restocking fee applies.", "source": "billing"},
    {"chunk_id": "doc_security", "content": "Data is encrypted at rest using AES-256 and in transit using TLS 1.3. All encryption keys are rotated every 90 days.", "source": "security"},
    {"chunk_id": "doc_payment",  "content": "Our enterprise payment terms are net 60 days from the date of invoice. A 2% early payment discount is available for payments within 10 days.", "source": "billing"},
    {"chunk_id": "doc_shipping", "content": "Standard shipping takes 5-7 business days within the continental US. Express shipping (2-day) is available for an additional $15.", "source": "logistics"},
    {"chunk_id": "doc_hr",       "content": "Employee termination requires a 30-day written notice period. Severance pay is calculated at 2 weeks per year of service.", "source": "hr"},
]

def simple_search(query: str, top_k: int = 3) -> list:
    query_words = set(query.lower().split())
    scored = []
    for doc in DOCUMENTS:
        doc_words = set(doc["content"].lower().split())
        overlap = len(query_words & doc_words)
        scored.append((overlap, doc))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [doc for score, doc in scored[:top_k]]

class SimpleRAGHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length)
        data = json.loads(body)
        
        query = data.get("query", "")
        top_k = data.get("top_k", 3)
        
        results = simple_search(query, top_k)
        
        response = {
            "data": {
                "chunks": [
                    {
                        "chunk_id": doc["chunk_id"],
                        "content": doc["content"],
                        "similarity": 0.95,
                        "metadata": {"source": doc["source"]}
                    }
                    for doc in results
                ]
            }
        }
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(response).encode('utf-8'))

    def log_message(self, format, *args):
        pass

server = HTTPServer(('127.0.0.1', 9876), SimpleRAGHandler)
server_thread = threading.Thread(target=server.serve_forever, daemon=True)
server_thread.start()

# ═══════════════════════════════════════════════════════════════════════════
# Main Demo with TUI
# ═══════════════════════════════════════════════════════════════════════════

console.print("\n🔬 [bold cyan]LongProbe - Complete Workflow Demo[/bold cyan]")
console.print("Testing RAG retrieval quality with automated regression detection\n")

# Sample questions
test_questions = [
    ("What is the refund policy?", ["billing"]),
    ("How is data encrypted?", ["security"]),
    ("What are the enterprise payment terms?", ["billing"]),
    ("How long does standard shipping take?", ["logistics"]),
    ("What is the employee termination notice period?", ["hr"]),
]

q_text = Text()
q_text.append("Sample Questions:\n\n", style="dim")
for idx, (q, tags) in enumerate(test_questions[:3], 1):
    q_text.append(f"{idx}. {q}\n", style="cyan")
q_text.append("\n...and 2 more", style="dim")

console.print(Panel(q_text, title="📋 Test Questions", border_style="blue"))

def create_progress_table(steps_data):
    table = Table(show_header=False, box=None, padding=(0, 1), expand=True)
    table.add_column("Step", style="bold", width=30)
    table.add_column("Status", width=5)
    table.add_column("Details", style="")
    
    for step_name, status, details in steps_data:
        if status == "done":
            table.add_row(step_name, "[green]✓[/green]", f"[green]{details}[/green]")
        elif status == "running":
            table.add_row(step_name, "[cyan]⚙️[/cyan]", f"[cyan]{details}[/cyan]")
        else:
            table.add_row(step_name, "[dim]⏳[/dim]", f"[dim]{details}[/dim]")
    
    return table

def show_questions_panel(questions_list):
    """Show sample questions being tested"""
    content = Text()
    content.append("Sample Questions:\n\n", style="bold")
    for i, (q, _) in enumerate(questions_list[:3], 1):
        content.append(f"{i}. ", style="cyan")
        content.append(f"{q}\n", style="white")
    if len(questions_list) > 3:
        content.append(f"\n...and {len(questions_list) - 3} more", style="dim")
    return Panel(content, border_style="cyan", title="📋 Test Questions")

def show_retrieval_panel(question, results):
    """Show what the API retrieved"""
    content = Text()
    content.append(f"Q: {question}\n\n", style="bold cyan")
    content.append("Retrieved Chunks:\n", style="bold")
    for i, r in enumerate(results[:2], 1):
        content.append(f"\n{i}. ", style="green")
        score = r.get('similarity', r.get('score', 0))
        content.append(f"[score: {score:.3f}]\n", style="dim")
        chunk_text = r.get('content', r.get('text', ''))[:80]
        content.append(f"   \"{chunk_text}...\"\n", style="white")
    if len(results) > 2:
        content.append(f"\n   ...and {len(results) - 2} more chunk(s)", style="dim")
    return Panel(content, border_style="green", title="✓ Retrieval Success")

def show_regression_panel(question_id, question, missing_chunk):
    """Show regression details"""
    content = Text()
    content.append(f"Question: {question}\n\n", style="bold yellow")
    content.append("Missing Chunk:\n", style="bold red")
    content.append(f"\"{missing_chunk[:100]}...\"\n\n", style="white")
    content.append("This chunk was in the baseline but is now missing!", style="red")
    return Panel(content, border_style="red", title=f"⚠️  Regression: {question_id}")

# Define test questions upfront
test_questions = [
    ("What is the refund policy?", ["doc:billing"]),
    ("How is data encrypted?", ["doc:security"]),
    ("What are the enterprise payment terms?", ["doc:billing"]),
    ("How long does shipping take?", ["doc:logistics"]),
    ("What is the employee termination policy?", ["doc:hr"]),
]

# Show what questions we'll test
console.print(show_questions_panel(test_questions))
time.sleep(2.5)

# Initialize steps
steps = [
    ("1. Start RAG Service", "running", "Starting server..."),
    ("2. Build Golden Set", "pending", "Waiting..."),
    ("3. Run Initial Check", "pending", "Waiting..."),
    ("4. Save Baseline", "pending", "Waiting..."),
    ("5. Simulate Pipeline Update", "pending", "Waiting..."),
    ("6. Detect Regression", "pending", "Waiting..."),
]

with Live(console=console, refresh_per_second=10) as live:
    # Step 1: Start API
    live.update(Panel(create_progress_table(steps), title="🔄 Workflow Progress", border_style="cyan"))
    time.sleep(1)
    
    steps[0] = ("1. Start RAG Service", "done", f"Running on port 9876 ({len(DOCUMENTS)} docs)")
    live.update(Panel(create_progress_table(steps), title="🔄 Workflow Progress", border_style="cyan"))
    time.sleep(0.8)
    
    # Step 2: Build Golden Set
    steps[1] = ("2. Build Golden Set", "running", "Auto-capturing from API...")
    live.update(Panel(create_progress_table(steps), title="🔄 Workflow Progress", border_style="cyan"))
    
    from longprobe.adapters.http import HttpAdapter
    from longprobe.config import HttpRetrieverConfig, HttpResponseMapping
    from longprobe.core.golden import GoldenSet, GoldenQuestion, generate_question_id
    
    http_config = HttpRetrieverConfig(
        url="http://127.0.0.1:9876",
        method="POST",
        body_template='{"query": "{question}", "top_k": {top_k}}',
        headers={},
        response_mapping=HttpResponseMapping(
            results_path="data.chunks",
            id_field="chunk_id",
            text_field="content",
            score_field="similarity",
        ),
        timeout=10,
    )
    
    adapter = HttpAdapter(config=http_config)
    
    golden_questions = []
    first_question_results = None
    
    for idx, (question_text, tags) in enumerate(test_questions):
        results = adapter.retrieve(query=question_text, top_k=3)
        required_chunks = [r["text"] for r in results if r["text"]]
        gq = GoldenQuestion(
            id=generate_question_id(question_text),
            question=question_text,
            required_chunks=required_chunks,
            match_mode="text",
            status="approved",
            top_k=3,
            tags=tags,
        )
        golden_questions.append(gq)
        
        # Save first question results to show later
        if idx == 0:
            first_question_results = results
    
    golden_set = GoldenSet(
        name="company-docs-regression",
        version="1.0",
        questions=golden_questions,
    )
    golden_set.to_yaml(GOLDENS_PATH)
    
    steps[1] = ("2. Build Golden Set", "done", f"Captured {len(golden_questions)} questions (status: approved)")
    live.update(Panel(create_progress_table(steps), title="🔄 Workflow Progress", border_style="cyan"))
    time.sleep(1)
    
    # Show example retrieval in the live context
    retrieval_display = Group(
        create_progress_table(steps),
        Text(""),
        show_retrieval_panel(test_questions[0][0], first_question_results)
    )
    live.update(Panel(retrieval_display, title="🔄 Workflow Progress", border_style="cyan"))
    time.sleep(4)
    
    # Continue with step 3
    live.update(Panel(create_progress_table(steps), title="🔄 Workflow Progress", border_style="cyan"))
    
    
    # Step 3: Run Initial Check
    steps[2] = ("3. Run Initial Check", "running", "Testing retrieval...")
    live.update(Panel(create_progress_table(steps), title="🔄 Workflow Progress", border_style="cyan"))
    
    from longprobe.core.scorer import RecallScorer
    
    scorer = RecallScorer(recall_threshold=0.8)
    report = scorer.score_all(golden_set, adapter.retrieve)
    
    steps[2] = ("3. Run Initial Check", "done", f"Recall: {report.overall_recall:.1%} | Pass: {report.pass_rate:.1%}")
    live.update(Panel(create_progress_table(steps), title="🔄 Workflow Progress", border_style="cyan"))
    time.sleep(1.2)
    
    # Step 4: Save Baseline
    steps[3] = ("4. Save Baseline", "running", "Saving to SQLite...")
    live.update(Panel(create_progress_table(steps), title="🔄 Workflow Progress", border_style="cyan"))
    
    from longprobe.core.baseline import BaselineStore
    
    store = BaselineStore(db_path=os.path.join(BASELINE_PATH, "baselines.db"))
    store.save(report, label="latest")
    
    steps[3] = ("4. Save Baseline", "done", "Baseline 'latest' saved")
    live.update(Panel(create_progress_table(steps), title="🔄 Workflow Progress", border_style="cyan"))
    time.sleep(1.2)
    
    # Step 5: Simulate Pipeline Update
    steps[4] = ("5. Simulate Pipeline Update", "running", "Simulating chunk removal...")
    live.update(Panel(create_progress_table(steps), title="🔄 Workflow Progress", border_style="cyan"))
    time.sleep(1.5)
    
    removed_doc = next((d for d in DOCUMENTS if d["chunk_id"] == "doc_refund"), None)
    DOCUMENTS[:] = [d for d in DOCUMENTS if d["chunk_id"] != "doc_refund"]
    
    steps[4] = ("5. Simulate Pipeline Update", "done", f"Removed 1 chunk ({len(DOCUMENTS)} remain)")
    live.update(Panel(create_progress_table(steps), title="🔄 Workflow Progress", border_style="cyan"))
    time.sleep(1.2)
    
    # Step 6: Detect Regression
    steps[5] = ("6. Detect Regression", "running", "Re-running tests...")
    live.update(Panel(create_progress_table(steps), title="🔄 Workflow Progress", border_style="cyan"))
    
    report_after = scorer.score_all(golden_set, adapter.retrieve)
    baseline = store.load("latest")
    if baseline:
        report_after.baseline_recall = baseline.overall_recall
        report_after.recall_delta = report_after.overall_recall - baseline.overall_recall
    
    steps[5] = ("6. Detect Regression", "done", f"Recall: {report_after.overall_recall:.1%} (Δ {report_after.recall_delta:+.1%})")
    live.update(Panel(create_progress_table(steps), title="🔄 Workflow Progress", border_style="green"))
    time.sleep(1.5)
    
    # Show regression details in the live context
    diff_result = store.diff(report_after, baseline)
    if diff_result.get("regressions"):
        first_reg = diff_result["regressions"][0]
        reg_question = next((q for q in golden_set.questions if q.id == first_reg["question_id"]), None)
        if reg_question and first_reg.get("newly_lost_chunks"):
            regression_display = Group(
                create_progress_table(steps),
                Text(""),
                show_regression_panel(
                    first_reg["question_id"],
                    reg_question.question,
                    first_reg["newly_lost_chunks"][0]
                )
            )
            live.update(Panel(regression_display, title="🔄 Workflow Progress", border_style="green"))
            time.sleep(4)

# Show detailed results
console.print()

# Results table
results_table = Table(title="📊 Regression Detection Results", show_header=True, expand=True, border_style="yellow")
results_table.add_column("Metric", style="bold")
results_table.add_column("Before", justify="right")
results_table.add_column("After", justify="right")
results_table.add_column("Change", justify="right")

results_table.add_row(
    "Overall Recall",
    f"[green]{baseline.overall_recall:.1%}[/green]",
    f"[yellow]{report_after.overall_recall:.1%}[/yellow]",
    f"[red]{report_after.recall_delta:+.1%}[/red]"
)
results_table.add_row(
    "Pass Rate",
    f"[green]{baseline.pass_rate:.1%}[/green]",
    f"[yellow]{report_after.pass_rate:.1%}[/yellow]",
    f"[red]{report_after.pass_rate - baseline.pass_rate:+.1%}[/red]"
)
results_table.add_row(
    "Failed Tests",
    f"[green]0[/green]",
    f"[red]{sum(1 for r in report_after.results if not r.passed)}[/red]",
    f"[red]+{sum(1 for r in report_after.results if not r.passed)}[/red]"
)

console.print(results_table)

console.print("\n[bold green]✅ Demo Complete![/bold green]")
console.print("[dim]LongProbe detected the regression automatically and showed exactly what broke.[/dim]\n")

server.shutdown()
