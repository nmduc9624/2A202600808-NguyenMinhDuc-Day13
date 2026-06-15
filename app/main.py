from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from structlog.contextvars import bind_contextvars

from .agent import LabAgent
from .incidents import disable, enable, status
from .logging_config import configure_logging, get_logger
from .metrics import record_error, snapshot
from .middleware import CorrelationIdMiddleware
from .pii import hash_user_id, summarize_text
from .schemas import ChatRequest, ChatResponse
from .tracing import flush_traces, tracing_enabled

configure_logging()
log = get_logger()
app = FastAPI(title="Day 13 Observability Lab")
app.add_middleware(CorrelationIdMiddleware)
agent = LabAgent()


@app.on_event("startup")
async def startup() -> None:
    log.info(
        "app_started",
        service=os.getenv("APP_NAME", "day13-observability-lab"),
        env=os.getenv("APP_ENV", "dev"),
        payload={"tracing_enabled": tracing_enabled()},
    )


@app.on_event("shutdown")
async def shutdown() -> None:
    flush_traces()


@app.get("/health")
async def health() -> dict:
    return {"ok": True, "tracing_enabled": tracing_enabled(), "incidents": status()}


@app.get("/metrics")
async def metrics() -> dict:
    return snapshot()


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard() -> HTMLResponse:
    return HTMLResponse(
        """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Day 13 Observability Dashboard</title>
  <style>
    :root {
      color-scheme: light;
      font-family: Inter, Segoe UI, Arial, sans-serif;
      --bg: #f5f7f9;
      --panel: #ffffff;
      --ink: #17202a;
      --muted: #637083;
      --line: #d9e0e8;
      --accent: #136f63;
      --warn: #c05621;
      --bad: #b42318;
    }
    * { box-sizing: border-box; }
    body { margin: 0; background: var(--bg); color: var(--ink); }
    header {
      display: flex; align-items: center; justify-content: space-between;
      padding: 18px 24px; border-bottom: 1px solid var(--line); background: #fff;
    }
    h1 { margin: 0; font-size: 22px; font-weight: 700; letter-spacing: 0; }
    .meta { color: var(--muted); font-size: 13px; }
    main { padding: 18px 24px 28px; }
    .grid { display: grid; grid-template-columns: repeat(3, minmax(220px, 1fr)); gap: 14px; }
    .panel { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 14px; min-height: 168px; }
    .panel h2 { margin: 0 0 12px; font-size: 14px; font-weight: 700; color: #273444; }
    .big { font-size: 32px; font-weight: 750; line-height: 1; }
    .sub { margin-top: 8px; color: var(--muted); font-size: 13px; }
    .row { display: flex; justify-content: space-between; gap: 12px; margin: 8px 0; font-size: 14px; }
    .bar { height: 10px; background: #edf1f5; border-radius: 999px; overflow: hidden; margin-top: 10px; }
    .fill { height: 100%; width: 0%; background: var(--accent); transition: width 0.2s ease; }
    .fill.warn { background: var(--warn); }
    .fill.bad { background: var(--bad); }
    .spark { width: 100%; height: 48px; margin-top: 10px; }
    code { font-family: Consolas, monospace; font-size: 12px; }
    @media (max-width: 900px) { .grid { grid-template-columns: repeat(2, minmax(220px, 1fr)); } }
    @media (max-width: 620px) { header { align-items: flex-start; flex-direction: column; gap: 6px; } .grid { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <header>
    <h1>Day 13 Observability Dashboard</h1>
    <div class="meta">Range: 1h · Refresh: 15s · Source: <code>/metrics</code></div>
  </header>
  <main class="grid">
    <section class="panel">
      <h2>Latency P50/P95/P99</h2>
      <div class="row"><span>P50</span><strong id="p50">0 ms</strong></div>
      <div class="row"><span>P95</span><strong id="p95">0 ms</strong></div>
      <div class="row"><span>P99</span><strong id="p99">0 ms</strong></div>
      <div class="bar"><div id="latency-bar" class="fill"></div></div>
      <div class="sub">SLO line: P95 &lt; 3000 ms</div>
    </section>
    <section class="panel">
      <h2>Traffic</h2>
      <div id="traffic" class="big">0</div>
      <div class="sub">Total requests observed</div>
      <svg id="traffic-spark" class="spark" viewBox="0 0 240 48" preserveAspectRatio="none"></svg>
    </section>
    <section class="panel">
      <h2>Error Rate</h2>
      <div id="error-rate" class="big">0%</div>
      <div id="errors" class="sub">No errors</div>
      <div class="bar"><div id="error-bar" class="fill"></div></div>
      <div class="sub">Alert line: &gt; 5% for 5m</div>
    </section>
    <section class="panel">
      <h2>Cost Over Time</h2>
      <div id="cost" class="big">$0.0000</div>
      <div class="sub">Total estimated cost</div>
      <svg id="cost-spark" class="spark" viewBox="0 0 240 48" preserveAspectRatio="none"></svg>
    </section>
    <section class="panel">
      <h2>Tokens In/Out</h2>
      <div class="row"><span>Input</span><strong id="tokens-in">0</strong></div>
      <div class="row"><span>Output</span><strong id="tokens-out">0</strong></div>
      <div class="sub">Token totals from agent usage</div>
    </section>
    <section class="panel">
      <h2>Quality Proxy</h2>
      <div id="quality" class="big">0.00</div>
      <div class="bar"><div id="quality-bar" class="fill"></div></div>
      <div class="sub">Heuristic average, target ≥ 0.75</div>
    </section>
  </main>
  <script>
    const history = { traffic: [], cost: [] };
    const fmtMs = v => `${Math.round(v || 0)} ms`;
    const pct = v => `${(v || 0).toFixed(1)}%`;

    function drawSpark(id, values) {
      const svg = document.getElementById(id);
      const items = values.slice(-30);
      svg.innerHTML = "";
      if (items.length < 2) return;
      const max = Math.max(...items, 1);
      const points = items.map((v, i) => {
        const x = (i / (items.length - 1)) * 240;
        const y = 44 - ((v / max) * 38);
        return `${x},${y}`;
      }).join(" ");
      const polyline = document.createElementNS("http://www.w3.org/2000/svg", "polyline");
      polyline.setAttribute("fill", "none");
      polyline.setAttribute("stroke", "#136f63");
      polyline.setAttribute("stroke-width", "3");
      polyline.setAttribute("points", points);
      svg.appendChild(polyline);
    }

    function setBar(id, ratio, status = "") {
      const el = document.getElementById(id);
      el.className = `fill ${status}`;
      el.style.width = `${Math.max(0, Math.min(100, ratio * 100))}%`;
    }

    async function refresh() {
      const res = await fetch("/metrics", { cache: "no-store" });
      const data = await res.json();
      const errorTotal = Object.values(data.error_breakdown || {}).reduce((a, b) => a + b, 0);
      const attempts = Math.max(1, (data.traffic || 0) + errorTotal);
      const errorRate = (errorTotal / attempts) * 100;

      document.getElementById("p50").textContent = fmtMs(data.latency_p50);
      document.getElementById("p95").textContent = fmtMs(data.latency_p95);
      document.getElementById("p99").textContent = fmtMs(data.latency_p99);
      document.getElementById("traffic").textContent = data.traffic || 0;
      document.getElementById("error-rate").textContent = pct(errorRate);
      document.getElementById("errors").textContent = errorTotal
        ? JSON.stringify(data.error_breakdown)
        : "No errors";
      document.getElementById("cost").textContent = `$${Number(data.total_cost_usd || 0).toFixed(4)}`;
      document.getElementById("tokens-in").textContent = data.tokens_in_total || 0;
      document.getElementById("tokens-out").textContent = data.tokens_out_total || 0;
      document.getElementById("quality").textContent = Number(data.quality_avg || 0).toFixed(2);

      setBar("latency-bar", (data.latency_p95 || 0) / 3000, data.latency_p95 > 5000 ? "bad" : data.latency_p95 > 3000 ? "warn" : "");
      setBar("error-bar", errorRate / 5, errorRate > 5 ? "bad" : "");
      setBar("quality-bar", (data.quality_avg || 0) / 0.75, data.quality_avg < 0.75 ? "warn" : "");

      history.traffic.push(data.traffic || 0);
      history.cost.push(Number(data.total_cost_usd || 0));
      drawSpark("traffic-spark", history.traffic);
      drawSpark("cost-spark", history.cost);
    }

    refresh();
    setInterval(refresh, 15000);
  </script>
</body>
</html>
        """.strip()
    )


@app.post("/chat", response_model=ChatResponse)
async def chat(request: Request, body: ChatRequest) -> ChatResponse:
    bind_contextvars(
        env=os.getenv("APP_ENV", "dev"),
        user_id_hash=hash_user_id(body.user_id),
        session_id=body.session_id,
        feature=body.feature,
        model=agent.model,
    )

    log.info(
        "request_received",
        service="api",
        payload={"message_preview": summarize_text(body.message)},
    )
    try:
        result = agent.run(
            user_id=body.user_id,
            feature=body.feature,
            session_id=body.session_id,
            message=body.message,
            correlation_id=request.state.correlation_id,
        )
        log.info(
            "response_sent",
            service="api",
            latency_ms=result.latency_ms,
            tokens_in=result.tokens_in,
            tokens_out=result.tokens_out,
            cost_usd=result.cost_usd,
            payload={"answer_preview": summarize_text(result.answer)},
        )
        flush_traces()
        return ChatResponse(
            answer=result.answer,
            correlation_id=request.state.correlation_id,
            latency_ms=result.latency_ms,
            tokens_in=result.tokens_in,
            tokens_out=result.tokens_out,
            cost_usd=result.cost_usd,
            quality_score=result.quality_score,
        )
    except Exception as exc:  # pragma: no cover
        error_type = type(exc).__name__
        record_error(error_type)
        log.error(
            "request_failed",
            service="api",
            error_type=error_type,
            payload={"detail": str(exc), "message_preview": summarize_text(body.message)},
        )
        flush_traces()
        raise HTTPException(status_code=500, detail=error_type) from exc


@app.post("/incidents/{name}/enable")
async def enable_incident(name: str) -> JSONResponse:
    try:
        enable(name)
        log.warning("incident_enabled", service="control", payload={"name": name})
        return JSONResponse({"ok": True, "incidents": status()})
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/incidents/{name}/disable")
async def disable_incident(name: str) -> JSONResponse:
    try:
        disable(name)
        log.warning("incident_disabled", service="control", payload={"name": name})
        return JSONResponse({"ok": True, "incidents": status()})
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
