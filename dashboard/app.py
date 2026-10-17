from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse

from core.config import DATABASE_PATH
from core.page_opener import PageOpenerService, load_pages
from database.repository import Repository

ROOT = Path(__file__).resolve().parents[1]
PAGES_PATH = ROOT / "config" / "pages_to_open.json"
pages = load_pages(PAGES_PATH)
repository = Repository(DATABASE_PATH)
service = PageOpenerService(pages, repository)


@asynccontextmanager
async def lifespan(app: FastAPI):
    service.start()
    yield
    service.stop()


app = FastAPI(title="Agendador de páginas", lifespan=lifespan)


@app.get("/", response_class=HTMLResponse)
async def dashboard() -> str:
    return """<!doctype html><html lang="pt-br"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Abertura agendada de páginas</title>
    <style>body{font:16px system-ui;max-width:900px;margin:40px auto;padding:0 20px;color:#172033}table{border-collapse:collapse;width:100%;margin-top:20px}td,th{padding:10px;border-bottom:1px solid #ddd;text-align:left}button{padding:9px 14px;margin:8px 8px 8px 0}.note{background:#eef4ff;padding:12px;border-radius:8px}</style>
    <h1>Abertura agendada de páginas</h1><p class="note">Este painel apenas abre as URLs configuradas no navegador padrão a cada 2 horas. Ele não faz login nem clica em elementos da página.</p>
    <p id="schedule">Carregando agendamento…</p><button onclick="openNow()">Abrir agora</button><button onclick="togglePause()">Pausar/retomar agendamento</button>
    <table><thead><tr><th>Nome</th><th>URL</th><th>Status</th></tr></thead><tbody id="pages"></tbody></table><h2>Últimas aberturas</h2><pre id="history">Carregando…</pre>
    <script>
    async function api(path,method='GET'){return fetch(path,{method})}
    async function load(){const r=await api('/api/pages');if(!r.ok){document.querySelector('#schedule').textContent='Falha ao carregar a lista.';return}const d=await r.json();document.querySelector('#schedule').textContent=`Próxima abertura automática: ${d.next_run||'não agendada'} · Fuso: America/Sao_Paulo · ${d.paused?'Pausado':'Ativo'}`;const body=document.querySelector('#pages');body.replaceChildren();for(const p of d.pages){const tr=document.createElement('tr');for(const v of [p.name,p.url,p.active?'Ativo':'Desativado']){const td=document.createElement('td');td.textContent=v;tr.appendChild(td)}body.appendChild(tr)}const h=await api('/api/history');const hd=await h.json();document.querySelector('#history').textContent=JSON.stringify(hd.runs,null,2)}
    async function openNow(){const r=await api('/api/open-now','POST');alert(JSON.stringify(await r.json()));load()}
    async function togglePause(){const r=await api('/api/pause','POST');alert(JSON.stringify(await r.json()));load()}
    load();
    </script></html>"""


@app.get("/mobile", response_class=HTMLResponse)
async def mobile_dashboard() -> str:
    """Painel otimizado para abrir as páginas diretamente no navegador do celular."""
    return """<!doctype html><html lang="pt-br"><head><meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
    <meta name="theme-color" content="#10183b"><title>Bônus · Celular</title>
    <style>
    :root{color-scheme:dark;font:16px system-ui,sans-serif;background:#0a1028;color:#f3f5ff}
    *{box-sizing:border-box}body{margin:0;padding:env(safe-area-inset-top) 16px env(safe-area-inset-bottom);max-width:680px;margin-inline:auto}
    header{padding:26px 4px 16px}h1{font-size:1.55rem;margin:0 0 8px}.muted{color:#b7c2eb;line-height:1.45}
    .timer,.card{background:#151f49;border:1px solid #34447f;border-radius:16px;padding:16px;margin:12px 0}
    .timer strong{display:block;font-size:1.1rem;margin-bottom:6px}.card h2{font-size:1.05rem;margin:0 0 8px;overflow-wrap:anywhere}
    .url{font-size:.82rem;color:#b7c2eb;overflow-wrap:anywhere;margin:0 0 14px}
    .open{display:flex;align-items:center;justify-content:center;min-height:50px;width:100%;border-radius:12px;background:#ffd66b;color:#241a00;font-weight:700;text-decoration:none}
    .open-all{display:flex;align-items:center;justify-content:center;min-height:54px;width:100%;border:0;border-radius:13px;background:#45d483;color:#062416;font-size:1rem;font-weight:800;margin:10px 0 16px}
    .empty{padding:18px;background:#151f49;border-radius:12px}.foot{font-size:.85rem;color:#aeb9e5;padding:10px 4px 28px}
    </style></head><body><header><h1>Abrir páginas de bônus</h1>
    <div class="muted">Toque em “Abrir página” para abrir no navegador deste celular. O painel não faz login nem clica na página.</div></header>
    <section class="timer"><strong id="clock">Carregando páginas…</strong><span class="muted" id="hint">Atualiza a lista ao abrir ou recarregar esta tela.</span></section>
    <button class="open-all" id="openAll" type="button" onclick="openAllPages()">Abrir todas as páginas</button>
    <p class="muted" id="openStatus" aria-live="polite"></p><main id="list"></main><p class="foot">Para usar: deixe o computador e o servidor ligados, conecte o celular à mesma rede Wi-Fi e abra este endereço: <b>http://IP-DO-COMPUTADOR:8000/mobile</b>. O navegador pode bloquear aberturas em lote ou trazer uma aba para frente. Se isso ocorrer, permita pop-ups para este painel; o navegador controla se as novas abas ficam em segundo plano.</p>
    <script>
    let activePages=[];
    async function load(){const title=document.querySelector('#clock'),list=document.querySelector('#list');try{const r=await fetch('/api/pages',{cache:'no-store'});if(!r.ok)throw Error();const d=await r.json();activePages=d.pages.filter(p=>p.active);title.textContent=activePages.length?`${activePages.length} página(s) ativa(s)`:'Nenhuma página ativa';document.querySelector('#openAll').disabled=!activePages.length;list.replaceChildren();if(!activePages.length){list.innerHTML='<div class="empty">Adicione URLs em config/pages_to_open.json.</div>';return}for(const p of activePages){const card=document.createElement('article');card.className='card';const h=document.createElement('h2');h.textContent=p.name;const url=document.createElement('p');url.className='url';url.textContent=p.url;const a=document.createElement('a');a.className='open';a.href=p.url;a.target='_blank';a.rel='noopener noreferrer';a.textContent='Abrir página';card.append(h,url,a);list.append(card)}}catch(e){title.textContent='Não foi possível carregar as páginas';document.querySelector('#openAll').disabled=true;list.innerHTML='<div class="empty">Confira se o servidor está ligado e se o celular está na mesma rede Wi-Fi.</div>'}}
    function openAllPages(){const status=document.querySelector('#openStatus');if(!activePages.length)return;for(const p of activePages){window.open(p.url,'_blank','noopener,noreferrer')}status.textContent=`Pedido enviado para abrir ${activePages.length} página(s). Se alguma não abriu, permita pop-ups para este painel e use os botões individuais.`}
    load();
    </script></body></html>"""


@app.get("/api/pages")
async def list_pages():
    return {
        "pages": [{"id": p.id, "name": p.name, "url": p.url, "active": p.active} for p in pages],
        "next_run": service.next_run(),
        "paused": service.paused,
    }


def require_local(request: Request) -> None:
    host = request.client.host if request.client else ""
    if host not in {"127.0.0.1", "::1", "localhost"}:
        raise HTTPException(status_code=403, detail="Ação disponível apenas no computador do servidor")


@app.post("/api/open-now")
async def open_now(request: Request):
    require_local(request)
    return await service.open_pages(force=True)


@app.post("/api/pause")
async def pause(request: Request):
    require_local(request)
    if service.paused:
        service.resume()
    else:
        service.pause()
    return {"paused": service.paused}


@app.get("/api/history")
async def history():
    return {"summary": repository.summary(), "runs": repository.history(50)}
