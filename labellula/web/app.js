// Labellula: interfaccia di ricerca (HTML5 + JavaScript, senza librerie esterne)
"use strict";

const $ = (id) => document.getElementById(id);
const stato = { filtri: {}, pagina: 1, totale: 0, risultati: [], aperta: -1, info: {}, simili: null };
const CAMPI = ["q", "modo", "categoria", "anno_da", "anno_a", "persona", "cartella", "verificare"];
const NOMI_FILTRI = { categoria: "categoria", anno_da: "dal", anno_a: "al", persona: "persona",
  cartella: "cartella", verificare: "da verificare" };

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

// memoria locale del browser (ultime ricerche, preferite, ultima cartella): se non c'è, si fa senza
const memoria = {
  leggi(k, base) { try { return JSON.parse(localStorage.getItem("labellula." + k)) ?? base; } catch { return base; } },
  scrivi(k, v) { try { localStorage.setItem("labellula." + k, JSON.stringify(v)); } catch { /* niente */ } },
};

// evidenzia le parole cercate (anche come inizio di parola, senza badare agli accenti)
function normalizza(s) { return s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase(); }
function evidenzia(testo, q) {
  const parole = (q || "").split(/[^\p{L}\p{N}]+/u).filter((p) => p.length > 1).map(normalizza);
  if (!parole.length || !testo) return esc(testo);
  // Si normalizza un carattere alla volta e si ricorda da quale carattere originale viene ogni lettera:
  // così l'evidenziazione resta al posto giusto anche quando il testo normalizzato ha un'altra lunghezza
  // (testi già scomposti NFD, legature, emoji).
  const car = Array.from(String(testo));
  let norm = "";
  const origine = [];
  car.forEach((c, i) => { const n = normalizza(c); norm += n; for (let k = 0; k < n.length; k++) origine.push(i); });
  const segni = new Array(car.length).fill(false);
  for (const p of parole) {
    const re = new RegExp("(^|[^\\p{L}\\p{N}])(" + p.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + ")", "gu");
    let m;
    while ((m = re.exec(norm))) {
      const inizio = m.index + m[1].length;
      for (let i = inizio; i < inizio + m[2].length; i++) segni[origine[i]] = true;
      if (m[0].length === 0) re.lastIndex++;
    }
  }
  // accenti staccati (NFD) e simili: seguono la lettera a cui sono attaccati
  for (let i = 1; i < car.length; i++) if (!normalizza(car[i])) segni[i] = segni[i - 1];
  let out = "", dentro = false;
  for (let i = 0; i < car.length; i++) {
    if (segni[i] && !dentro) { out += "<mark>"; dentro = true; }
    if (!segni[i] && dentro) { out += "</mark>"; dentro = false; }
    out += esc(car[i]);
  }
  return out + (dentro ? "</mark>" : "");
}

function url(percorso, parametri = {}) {
  const u = new URL(percorso, location.href);
  for (const [k, v] of Object.entries(parametri)) if (v !== "" && v != null) u.searchParams.set(k, v);
  return u;
}
async function api(percorso, parametri = {}) {
  const r = await fetch(url(percorso, parametri));
  const j = await r.json();
  if (!r.ok) throw new Error(j.errore || r.statusText);
  return j;
}
async function invia(percorso, corpo = {}) {
  const r = await fetch(percorso, { method: "POST", body: JSON.stringify(corpo),
    headers: { "Content-Type": "application/json", "X-Labellula": "1" } });
  const j = await r.json();
  if (!r.ok) throw new Error(j.errore || r.statusText);
  return j;
}

// ------------------------------------------------------------------ form e indirizzo
function leggiForm() {
  const f = {};
  for (const c of ["q", "modo", "categoria", "anno_da", "anno_a", "persona"]) f[c] = $(c).value.trim();
  f.cartella = stato.filtri.cartella || "";
  f.verificare = $("verificare").checked ? "1" : "";
  return f;
}
function scriviForm(f) {
  for (const c of ["q", "modo", "categoria", "anno_da", "anno_a", "persona"]) $(c).value = f[c] || (c === "modo" ? "misto" : "");
  $("verificare").checked = f.verificare === "1";
  mostraFiltriAttivi(f);
}
// lo stato della ricerca sta nell'indirizzo (#q=...): si può salvare nei preferiti e tornare indietro
function daHash() {
  const p = new URLSearchParams(location.hash.slice(1));
  const f = {};
  for (const c of CAMPI) f[c] = p.get(c) || "";
  return f;
}
function aHash(f) {
  const p = new URLSearchParams();
  for (const c of CAMPI) if (f[c]) p.set(c, f[c]);
  const h = p.toString();
  if (location.hash.slice(1) !== h) history.pushState(null, "", h ? "#" + h : location.pathname);
}
function descriviRicerca(f) {
  const parti = [];
  if (f.q) parti.push(`“${f.q}”`);
  for (const [k, nome] of Object.entries(NOMI_FILTRI)) if (f[k]) parti.push(k === "verificare" ? nome : `${nome}: ${f[k]}`);
  return parti.join(" · ") || "tutte le foto";
}
function mostraFiltriAttivi(f) {
  const el = $("filtri-attivi");
  el.innerHTML = f.cartella
    ? `<span class="filtro">${T("Cartella")}: <b>${esc(f.cartella)}</b> <button class="link" data-togli="cartella" title="${T("Togli il filtro")}">✕</button></span>` : "";
}

// ------------------------------------------------------------------ ultime ricerche e preferite
function ricordaRicerca(f) {
  if (!f.q && !f.cartella && !f.categoria && !f.persona) return;
  const chiave = JSON.stringify(f);
  const ultime = memoria.leggi("ultime", []).filter((x) => JSON.stringify(x) !== chiave);
  ultime.unshift(f);
  memoria.scrivi("ultime", ultime.slice(0, 10));
  mostraUltime();
}
function mostraUltime() {
  const salvate = memoria.leggi("salvate", []);
  const ultime = memoria.leggi("ultime", []).slice(0, 6);
  const chip = (f, tipo, i) => `<button class="chip ${tipo}" data-ricerca="${tipo}:${i}" title="${esc(descriviRicerca(f))}">${tipo === "salvata" ? "★ " : ""}${esc(descriviRicerca(f)).slice(0, 40)}</button>`;
  $("ultime").innerHTML =
    (salvate.length ? salvate.map((f, i) => chip(f, "salvata", i)).join("") : "") +
    (ultime.length ? `<span class="tenue piccolo">${T("Ultime:")}</span>` + ultime.map((f, i) => chip(f, "ultima", i)).join("") : "");
}

// ------------------------------------------------------------------ filtri e statistiche
async function caricaFiltri() {
  const [f, info] = await Promise.all([api("/api/filtri"), api("/api/info")]);
  stato.info = info;
  for (const id of ["categoria", "anno_da", "anno_a", "persona"]) $(id).length = 1;
  for (const c of f.categorie) $("categoria").add(new Option(`${c.valore || T("(nessuna)")} (${c.n})`, c.valore));
  for (const a of f.anni) { $("anno_da").add(new Option(a, a)); $("anno_a").add(new Option(a, a)); }
  $("persona").hidden = !f.persone.length;
  for (const p of f.persone) $("persona").add(new Option(`${p.valore} (${p.n})`, p.valore));
  $("modo").hidden = !info.significato;
  $("info").textContent = T("Indice: {n} schede, aggiornato il {data}.", { n: Number(info.schede).toLocaleString(LOCALE), data: info.creato }) +
    (info.significato ? " " + T("Ricerca per significato attiva.") : "");
  try {     // quali modelli e quali versioni del prompt hanno scritto le schede
    const st = await api("/api/statistiche");
    if (st.modelli.length) $("info").textContent += " " + T("Schede scritte da:") + " " + st.modelli.map((m) =>
      `${(m.modello || T("sconosciuto")).replace(/\s*\(prompt/, ", prompt").replace(/\)$/, "")} (${m.n.toLocaleString(LOCALE)})`).join(" · ") + ".";
  } catch { /* niente */ }
  for (const id of ["f-dona", "cr-dona"]) { $(id).href = info.url_donazioni || "https://ctrlalt.museum/"; }
  $("b-descrivi").hidden = !info.lavori;
  const rete = info.rete || {};
  $("f-esci").hidden = rete.da_questo_computer !== false;      // chi entra dalla rete può uscire
  $("sez-rete").hidden = !rete.da_questo_computer;               // la rete si imposta solo da questo computer
  // dalla rete di casa: niente cambio di archivio né di Ollama (il server li rifiuta comunque)
  for (const el of document.querySelectorAll(".solo-locale")) el.hidden = rete.da_questo_computer === false;
  mostraRete(rete);
  if (info.in_demo) {
    $("fascia-testo").innerHTML = T("Stai guardando l'<b>archivio dimostrativo</b>: foto di ctrlalt.museum. Per le tue foto: <b>＋ Descrivi foto</b> › scegli la cartella › <b>Imposta come archivio</b>.");
  }
  if (info.riavvio_necessario) {          // il programma è stato aggiornato ma questo server è ancora quello vecchio
    $("fascia-testo").hidden = false;
    $("fascia-testo").innerHTML = T("<b>Labellula è stato aggiornato:</b> chiudi e riapri Labellula (doppio clic sull'icona) per usare la versione nuova.");
  }
}

// ------------------------------------------------------------------ risultati
function carta(r, i) {
  const b = document.createElement("button");
  b.className = "carta";
  b.dataset.i = i;
  const cartella = r.cartella ? r.cartella.split("/").pop() : "";
  const titolo = r.titolo || cartella || r.nome;
  const sotto = r.titolo ? cartella : "";
  b.innerHTML = `<img loading="lazy" src="/miniatura?id=${encodeURIComponent(r.id_foto)}" alt="">
    <div class="didascalia"><b title="${esc(r.cartella)}">${esc(titolo)}</b>
    ${sotto ? `<i>${esc(sotto)}</i>` : ""}<span>${esc(r.descrizione)}</span></div>`;
  b.querySelector("img").alt = (r.titolo || r.descrizione || "").slice(0, 120);
  b.addEventListener("click", () => apri(i));
  return b;
}

let numeroRicerca = 0;
async function cerca(nuova = true) {
  const mia = ++numeroRicerca;            // se parte un'altra ricerca, questa risposta va ignorata
  if (nuova) { stato.pagina = 1; stato.risultati = []; $("griglia").innerHTML = ""; }
  $("stato").textContent = T("Ricerca…");
  try {
    const r = stato.simili
      ? await api("/api/simili", { id: stato.simili.id })
      : await api("/api/cerca", { ...stato.filtri, pagina: stato.pagina });
    if (mia !== numeroRicerca) return;
    stato.totale = r.totale;
    const base = stato.risultati.length;
    stato.risultati.push(...r.risultati);
    const frammento = document.createDocumentFragment();
    r.risultati.forEach((x, k) => frammento.appendChild(carta(x, base + k)));
    $("griglia").appendChild(frammento);
    const n = r.totale.toLocaleString(LOCALE);
    if (stato.simili) {
      $("stato").innerHTML = T("Foto simili a <b>{nome}</b> ({n}).", { nome: esc(stato.simili.nome), n }) + ` <button class="link" id="esci-simili">${T("Torna alla ricerca")}</button>`;
      $("esci-simili").onclick = () => { stato.simili = null; cerca(true); };
    } else {
      const vuoto = r.totale === 0 && Number(stato.info.schede || 0) === 0;
      if (vuoto && stato.info.demo) {
        $("stato").innerHTML = T("L'archivio è ancora vuoto.") + ` <button class='principale' id='apri-demo'>${T("Guarda l'archivio dimostrativo di ctrlalt.museum")}</button> ` +
          T("oppure") + ` <button id='vuoto-descrivi'>${T("＋ Descrivi le tue foto")}</button>`;
        $("apri-demo").onclick = apriDemo;
        $("vuoto-descrivi").onclick = () => $("b-descrivi").click();
      } else {
        $("stato").textContent = r.totale === 0 ? T("Nessuna foto trovata. Prova con meno parole o togli un filtro.")
          : T("{n} foto", { n }) + (r.totale > stato.risultati.length ? T(", ne vedi {m}", { m: stato.risultati.length }) : "") + ".";
      }
    }
    $("altri").hidden = stato.simili || stato.risultati.length >= r.totale;
    $("b-esporta").href = url("/api/esporta.csv", stato.filtri).toString();
  } catch (e) {
    $("stato").textContent = T("Errore:") + " " + e.message;
  }
}

function riga(titolo, html) { return html ? `<h3>${T(titolo)}</h3><p>${html}</p>` : ""; }
function vuoto(s) { return !s || /^(nessun[oa]?|non determinabile|non ce ne sono|none|not determinable|nothing|aucune?|rien|keine?|nichts|ninguno|ninguna|nada)\.?$/i.test(String(s).trim()); }
function chips(testo, campo) {
  return String(testo || "").split(/\s*,\s*/).filter(Boolean)
    .map((p) => `<button class="chip" data-campo="${campo}" data-valore="${esc(p)}">${esc(p)}</button>`).join("");
}

async function apri(i) {
  if (i < 0 || i >= stato.risultati.length) return;
  stato.aperta = i;
  document.querySelectorAll(".carta.attiva").forEach((c) => c.classList.remove("attiva"));
  const c = document.querySelector(`.carta[data-i="${i}"]`);
  if (c) { c.classList.add("attiva"); c.scrollIntoView({ block: "nearest" }); }
  const r = stato.risultati[i];
  const id = encodeURIComponent(r.id_foto);
  $("pannello").hidden = false;
  $("p-nome").textContent = r.titolo || r.nome;
  $("p-img").src = `/miniatura?id=${id}&lato=1600`;
  $("p-img").alt = (r.titolo || r.descrizione || "").slice(0, 200);
  $("p-link").href = `/foto?id=${id}`;
  $("p-simili").hidden = !stato.info.significato;
  $("p-corpo").innerHTML = "<p>Caricamento…</p>";
  try {
    const s = await api("/api/scheda", { id: r.id_foto });
    stato.schedaAperta = s;
    const q = stato.filtri.q;
    const persone = s.persone_riconosciute
      ? s.persone_riconosciute.split(" | ").map((p) => `<button class="chip" data-campo="persona" data-valore="${esc(p)}">${esc(p)}</button>`).join("")
      : "";
    $("p-corpo").innerHTML =
      (s.avviso ? `<p class="avviso">${T("Il modello si era ripetuto: descrizione da controllare.")}</p>` : "") +
      (s.titolo ? `<p class="p-titolo">${evidenzia(s.titolo, q)}</p>` : "") +
      riga("Descrizione", evidenzia(s.descrizione, q)) +
      riga("Testi visibili", vuoto(s.testi) ? "" : evidenzia(s.testi, q)) +
      riga("Luogo e periodo", evidenzia(s.luogo, q)) +
      riga("Occasione", vuoto(s.occasione) ? "" : evidenzia(s.occasione, q)) +
      riga("Data", esc(s.data ? s.data.split("-").reverse().join("/") : (s.anno || ""))) +
      riga("Categoria", s.categoria ? `<button class="chip" data-campo="categoria" data-valore="${esc(s.categoria)}">${esc(s.categoria)}</button>` : "") +
      riga("Persone (dalla descrizione)", vuoto(s.persone_testo) ? "" : esc(s.persone_testo)) +
      riga("Persone riconosciute", persone) +
      riga("Aspetti fotografici", esc(s.fotografia)) +
      riga("Parole chiave", chips(s.parole_chiave, "q")) +
      (vuoto(s.dubbi) ? "" : `<h3>${T("Dubbi del modello")}</h3><p class="avviso">${esc(s.dubbi)}</p>`) +
      `<p class="tecnico">${esc(s.id_foto)}<br>${T("Generato con:")} ${esc(s.modello)}</p>`;
  } catch (e) {
    $("p-corpo").innerHTML = `<p>${T("Errore:")} ${esc(e.message)}</p>`;
  }
}
function chiudi() { $("pannello").hidden = true; stato.aperta = -1; }

function applica(f) { stato.simili = null; stato.filtri = f; scriviForm(f); aHash(f); ricordaRicerca(f); cerca(true); }

// ------------------------------------------------------------------ descrivere una cartella
const sfoglia = { percorso: "", inArchivio: true, inDemo: false };
async function apriCartella(percorso) {
  try {
    const r = await api("/api/cartelle", { percorso });
    sfoglia.percorso = r.percorso;
    sfoglia.padre = r.padre;
    $("c-percorso").value = r.percorso;
    $("c-su").disabled = r.padre === null || r.padre === undefined;
    $("c-elenco").innerHTML = r.cartelle.length
      ? r.cartelle.map((c) => `<li><button type="button" class="cartella" data-percorso="${esc(c.percorso)}">📁 ${esc(c.nome)}</button></li>`).join("")
      : `<li class="tenue">${T("Nessuna sottocartella.")}</li>`;
    $("c-info").textContent = r.percorso
      ? T("In questa cartella (senza le sottocartelle): {n} foto", { n: r.foto }) + (r.heic ? T(" (di cui {h} HEIC)", { h: r.heic }) : "") + T(", {s} già descritte.", { s: r.schede }) +
        (r.heic && stato.info.heic === false ? " ⚠ " + T("Le foto HEIC non si possono leggere: manca il pacchetto pillow-heif (rilancia l'installatore).") : "")
      : T("Scegli un'unità disco.");
    if (r.percorso) memoria.scrivi("cartella", r.percorso);
  } catch (e) {
    $("c-info").textContent = T("Errore:") + " " + e.message;
  }
}
async function contaFoto() {
  if (!sfoglia.percorso) return;
  $("c-info").textContent = T("Conto le foto, anche nelle sottocartelle…");
  try {
    const r = await api("/api/conta", { percorso: sfoglia.percorso, rifai: $("c-rifai").checked ? "1" : "",
      aggiorna: $("c-aggiorna").checked ? "1" : "" });
    sfoglia.inArchivio = r.in_archivio !== false; sfoglia.inDemo = !!r.in_demo;
    $("c-info").textContent = T("{n} foto in tutto, da descrivere: {d}", { n: r.totale.toLocaleString(LOCALE), d: r.da_fare.toLocaleString(LOCALE) }) +
      (r.da_fare ? " " + T("(circa {t} su questa GPU)", { t: r.minuti_stimati < 60 ? T("{m} minuti", { m: r.minuti_stimati }) : T("{o} ore", { o: (r.minuti_stimati / 60).toFixed(1) }) }) : "") + ".";
  } catch (e) { $("c-info").textContent = T("Errore:") + " " + e.message; }
}
async function avviaLavoro() {
  if (!sfoglia.percorso) return;
  // Le schede di una cartella fuori dall'archivio non entrano nella ricerca: meglio dirlo prima, non dopo.
  if ((!sfoglia.inArchivio || sfoglia.inDemo) && stato.info.rete && stato.info.rete.da_questo_computer === false) {
    $("c-info").textContent = T("Dalla rete si descrivono solo cartelle dell'archivio.");
    return;
  }
  if (!sfoglia.inArchivio || sfoglia.inDemo) {
    const domanda = sfoglia.inDemo
      ? T("Ora la ricerca mostra l'archivio dimostrativo. Uso \"{p}\" come tuo archivio, così le schede nuove si possono cercare?", { p: sfoglia.percorso })
      : T("\"{p}\" non fa parte dell'archivio della ricerca ({a}): le schede verrebbero scritte ma non le troveresti cercando.\nLa uso come archivio? (Annulla = descrivi soltanto)", { p: sfoglia.percorso, a: stato.info.archivio });
    if (confirm(domanda)) {
      try {
        const r = await invia("/api/archivio", { radice: sfoglia.percorso });
        $("c-archivio-attuale").textContent = r.archivio;
        stato.info.archivio = r.archivio; stato.info.in_demo = false;
        sfoglia.inArchivio = true; sfoglia.inDemo = false;
      } catch (e) { $("c-info").textContent = T("Errore:") + " " + e.message; return; }
    }
  }
  try {
    await invia("/api/lavoro", { cartella: sfoglia.percorso, rifai: $("c-rifai").checked, limite: $("c-prova").checked ? 20 : 0,
      aggiorna: $("c-aggiorna").checked, a_lotti: $("c-lotti").checked, modello: $("c-modello").value });
    $("d-descrivi").close();
    seguiLavoro();
  } catch (e) { $("c-info").textContent = T("Errore:") + " " + e.message; }
}
async function apriDemo() {
  $("stato").textContent = T("Preparo l'archivio dimostrativo…");
  try {
    await invia("/api/archivio", { radice: stato.info.demo });
    await caricaFiltri(); applica({});
  } catch (e) { $("stato").textContent = T("Errore:") + " " + e.message; }
}
async function impostaArchivio() {
  if (!sfoglia.percorso) return;
  if (!confirm(T("Usare \"{p}\" come archivio della ricerca?\nconfig.yaml viene aggiornato (con una copia di sicurezza) e l'indice ricostruito.", { p: sfoglia.percorso }))) return;
  $("c-info").textContent = T("Ricostruisco l'indice…");
  try {
    const r = await invia("/api/archivio", { radice: sfoglia.percorso });
    $("c-archivio-attuale").textContent = r.archivio;
    $("c-info").textContent = T("Fatto: la ricerca ora usa questa cartella.");
    await caricaFiltri(); applica({});
  } catch (e) { $("c-info").textContent = T("Errore:") + " " + e.message; }
}

let timerLavoro = null;
function durata(s) { return s == null ? "" : s < 90 ? `${s} s` : s < 5400 ? `${Math.round(s / 60)} min` : `${(s / 3600).toFixed(1)} ore`; }
async function seguiLavoro() {
  clearTimeout(timerLavoro);
  let s;
  try { s = await api("/api/lavoro"); } catch { return; }
  if (!s.fase) { $("lavoro").hidden = true; $("fascia-testo").hidden = false; return; }
  $("lavoro").hidden = false;
  $("fascia-testo").hidden = true;
  const nome = (s.cartella || "").split(/[\\/]/).pop();
  const lotto = s.lotti > 1 ? " · " + T("lotto {k}/{n} «{l}»", { k: s.lotto, n: s.lotti, l: s.nome_lotto || "" }) : "";
  $("l-fase").textContent = s.attivo ? T("Descrivo «{nome}»", { nome }) + lotto : s.fase === "errore" ? T("Errore") : `«${nome}»: ${T(s.fase)}`;
  const ultimo = (s.messaggi || []).slice(-1)[0] || "";
  const motore = s.modello ? " " + T("con {m}, prompt {p}", { m: s.modello, p: s.prompt }) : "";
  $("l-dettaglio").textContent = s.fase === "errore" ? s.errore
    : s.attivo && s.fase === "descrizione" && s.totale != null
      ? T("{f}/{t} foto", { f: s.fatte, t: s.totale }) + (s.secondi_mancanti ? T(", mancano circa {d}", { d: durata(s.secondi_mancanti) }) : "") +
        (s.in_corso ? " · " + T("ora:") + ` ${s.in_corso}${motore}` : "") +
        (s.titolo ? " · " + T("ultima:") + ` «${s.titolo}»${s.secondi_foto ? " " + T("in {s} s", { s: s.secondi_foto }) : ""}` : "")
      : s.attivo ? T(s.fase) + "… " + ultimo
      : s.risultato ? T("{f} schede scritte, {e} errori, {v} da verificare.", { f: s.risultato.fatte, e: s.risultato.errori, v: s.risultato.da_verificare }) : ultimo;
  $("l-barra").max = s.totale || 1;
  $("l-barra").value = s.fatte || 0;
  $("l-barra").hidden = !s.attivo;
  $("l-ferma").hidden = !s.attivo;
  $("l-chiudi").hidden = s.attivo;
  if (s.attivo) { stato.inCorso = true; timerLavoro = setTimeout(seguiLavoro, 2000); }
  else if (stato.inCorso) { stato.inCorso = false; await caricaFiltri(); cerca(true); }   // ricarica una volta a fine lavoro
}

// ------------------------------------------------------------------ eventi
document.addEventListener("click", (e) => {
  const chip = e.target.closest(".chip[data-campo]");
  if (chip) {
    const f = { ...stato.filtri };
    f[chip.dataset.campo] = chip.dataset.valore;
    if (chip.dataset.campo === "q") { f.categoria = ""; f.persona = ""; }
    chiudi();
    return applica(f);
  }
  const ric = e.target.closest("[data-ricerca]");
  if (ric) {
    const [tipo, i] = ric.dataset.ricerca.split(":");
    const lista = memoria.leggi(tipo === "salvata" ? "salvate" : "ultime", []);
    if (e.altKey && tipo === "salvata") { lista.splice(+i, 1); memoria.scrivi("salvate", lista); return mostraUltime(); }
    return applica({ ...lista[+i] });
  }
  const togli = e.target.closest("[data-togli]");
  if (togli) { const f = { ...stato.filtri }; f[togli.dataset.togli] = ""; return applica(f); }
  const cart = e.target.closest(".cartella[data-percorso]");
  if (cart) apriCartella(cart.dataset.percorso);
});
$("ricerca").addEventListener("submit", (e) => { e.preventDefault(); applica(leggiForm()); });
for (const c of ["modo", "categoria", "anno_da", "anno_a", "persona", "verificare"]) $(c).addEventListener("change", () => applica(leggiForm()));
$("altri").addEventListener("click", () => { stato.pagina++; cerca(false); });
$("chiudi").addEventListener("click", chiudi);
$("prec").addEventListener("click", () => apri(stato.aperta - 1));
$("succ").addEventListener("click", async () => {
  if (stato.aperta + 1 >= stato.risultati.length && stato.risultati.length < stato.totale) { stato.pagina++; await cerca(false); }
  apri(stato.aperta + 1);
});
$("p-simili").addEventListener("click", () => {
  const r = stato.risultati[stato.aperta];
  if (!r) return;
  chiudi(); stato.simili = { id: r.id_foto, nome: r.titolo || r.nome }; cerca(true);
});
$("p-cartella").addEventListener("click", () => {
  const r = stato.risultati[stato.aperta];
  if (!r) return;
  chiudi(); applica({ cartella: r.cartella || "" });
});
$("p-copia").addEventListener("click", async () => {
  const s = stato.schedaAperta;
  if (!s) return;
  const testo = [s.titolo, s.descrizione, s.testi && T("Testi visibili") + ": " + s.testi, s.luogo && T("Luogo e periodo") + ": " + s.luogo,
    s.occasione && T("Occasione") + ": " + s.occasione, s.parole_chiave && T("Parole chiave") + ": " + s.parole_chiave, s.id_foto].filter(Boolean).join("\n");
  try { await navigator.clipboard.writeText(testo); $("p-copia").textContent = T("Copiata ✓"); }
  catch { $("p-copia").textContent = T("Copia non riuscita"); }
  setTimeout(() => { $("p-copia").textContent = T("Copia scheda"); }, 1500);
});
$("b-salva").addEventListener("click", () => {
  const f = stato.filtri;
  const salvate = memoria.leggi("salvate", []).filter((x) => JSON.stringify(x) !== JSON.stringify(f));
  salvate.unshift(f);
  memoria.scrivi("salvate", salvate.slice(0, 12));
  mostraUltime();
  $("b-salva").textContent = T("★ Salvata");
  setTimeout(() => { $("b-salva").textContent = T("☆ Salva ricerca"); }, 1500);
});
async function caricaModelli() {
  try {
    const r = await api("/api/modelli");
    const sel = $("c-modello");
    sel.length = 0;
    const nomi = r.modelli.map((m) => m.nome);
    if (r.attuale && !nomi.includes(r.attuale)) nomi.unshift(r.attuale);
    for (const m of r.modelli) sel.add(new Option(`${m.nome} (${m.parametri}, ${m.dimensione_gb} GB)`, m.nome));
    if (r.attuale && !r.modelli.some((m) => m.nome === r.attuale)) sel.add(new Option(`${r.attuale} (${T("non installato?")})`, r.attuale), 0);
    sel.value = r.attuale;
    $("c-modello-nota").textContent = r.modelli.length > 1
      ? T("Le schede riportano sempre il modello che le ha scritte.") : T("Altri modelli: «ollama pull <nome>» (es. gemma3:12b).");
  } catch { $("c-modello-nota").textContent = T("Ollama non risponde."); }
}
function mostraEsitoOllama(r, usato) {
  const el = $("c-ollama-esito");
  el.hidden = false;
  el.className = "rientro piccolo " + (r.ok ? "esito-ok" : "esito-ko");
  if (!r.ok) { el.textContent = "✗ " + (r.errore || T("Ollama non risponde.")); return; }
  const modelli = (r.modelli_visione || []).map((m) => m.nome).join(", ") || T("nessun modello che vede le immagini");
  el.textContent = "✓ " + T("Ollama {v} risponde su {u} (rete {r}). Modelli: {m}.", { v: r.versione, u: r.url, r: T(r.rete), m: modelli }) +
    (r.ricerca_significato ? "" : " " + T("Manca bge-m3 per la ricerca per significato.")) +
    (usato ? (r.modello ? " " + T("In uso con {m}.", { m: r.modello }) : "") : " " + T("Premi «Usa» per descrivere le foto con questo Ollama.")) +
    (r.avviso ? " ⚠ " + r.avviso : "");
}
async function provaOllama(usa) {
  const indirizzo = $("c-ollama").value.trim();
  $("c-ollama-esito").hidden = false;
  $("c-ollama-esito").className = "rientro piccolo";
  $("c-ollama-esito").textContent = T("Provo a raggiungere Ollama…");
  try {
    const r = await invia(usa ? "/api/ollama" : "/api/ollama/prova", { indirizzo, modello: $("c-modello").value });
    mostraEsitoOllama(r, usa);
    if (usa && r.ok) {
      await caricaFiltri();
      await caricaModelli();
      const locale = document.querySelector('input[name="motore"][value="locale"]');
      if (locale) { locale.disabled = false; locale.checked = true; }
    }
  } catch (e) {
    const vecchio = /non trovato|non disponibile in questo server/.test(e.message);
    mostraEsitoOllama({ ok: false, errore: vecchio
      ? T("Il server di Labellula aperto è una versione precedente: chiudi e riapri Labellula (doppio clic sull'icona), poi riprova.")
      : e.message });
  }
}
$("c-ollama-prova").addEventListener("click", () => provaOllama(false));
$("c-ollama-usa").addEventListener("click", () => provaOllama(true));
$("c-ollama").addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); provaOllama(false); } });
$("b-descrivi").addEventListener("click", () => {
  const u = stato.info.ollama_url || "";
  $("c-ollama").value = /localhost|127\.0\.0\.1/.test(u) ? "" : u.replace(/^http:\/\//, "").replace(/:11434$/, "");
  $("c-archivio-attuale").textContent = stato.info.archivio || "";
  $("c-versione").textContent = stato.info.prompt || "ultimo";
  const hw = stato.info.hardware || {};
  const nomi = { ok: "adatto", limite: "al limite", da_provare: "da provare", insufficiente: "non adatto" };
  $("c-hardware").hidden = !hw.verdetto;
  if (hw.verdetto) {
    $("c-hardware").textContent = T("Questo computer{s}: {v} per descrivere in locale.", { s: hw.schede ? " (" + hw.schede + ")" : "", v: T(nomi[hw.verdetto] || hw.verdetto) }) + " " +
      (hw.prova && hw.prova.secondi_a_foto ? T("Prova: {s} s a foto con {m}.", { s: hw.prova.secondi_a_foto, m: hw.prova.modello }) + " " : "") + (LINGUA === "it" ? (hw.consiglio || "") : "");
    const locale = document.querySelector('input[name="motore"][value="locale"]');
    if (locale) locale.disabled = hw.verdetto === "insufficiente" && !stato.info.ollama_remoto;
    if (stato.info.ollama_remoto) $("c-hardware").textContent += " " + T("Le foto vengono descritte dall'Ollama di un altro computer della rete ({u}).", { u: stato.info.ollama_url });
  }
  caricaModelli();
  $("d-descrivi").showModal();
  apriCartella(memoria.leggi("cartella", "") || stato.info.archivio || "");
});
$("c-su").addEventListener("click", () => apriCartella(sfoglia.padre || ""));
$("c-vai").addEventListener("click", () => apriCartella($("c-percorso").value.trim()));
$("c-percorso").addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); apriCartella($("c-percorso").value.trim()); } });
$("c-conta").addEventListener("click", contaFoto);
$("c-avvia").addEventListener("click", avviaLavoro);
$("c-archivio").addEventListener("click", impostaArchivio);
$("l-ferma").addEventListener("click", async () => { try { await invia("/api/lavoro/ferma"); } catch { /* niente */ } seguiLavoro(); });
$("l-chiudi").addEventListener("click", () => { $("lavoro").hidden = true; $("fascia-testo").hidden = false; });
const GUIDA = "https://github.com/dinobaldi/labellula/blob/main/docs/GUIDA.md";
function mostraRete(r) {
  if (!r || !r.da_questo_computer) return;
  const indirizzi = (r.indirizzi || []).map((ip) => `http://${ip}:${r.porta}`).join("  oppure  ");
  $("r-stato").innerHTML = r.attiva && r.password
    ? T("<b>Attivo.</b> Dal telefono, sulla stessa Wi-Fi, apri: <b>{i}</b>", { i: esc(indirizzi) })
    : r.configurata && !r.attiva ? T("Impostato: chiudi e riapri Labellula (icona sul desktop) per attivarlo.")
    : !r.configurata && r.attiva ? T("Disattivato: chiudi e riapri Labellula per chiudere l'accesso dalla rete.")
    : T("Non attivo: la ricerca si apre solo da questo computer.");
  $("r-disattiva").hidden = !r.configurata;
  $("r-attiva").textContent = r.configurata ? T("Cambia la password") : T("Attiva l'accesso dalla rete");
}
async function impostaRete(attiva) {
  const p1 = $("r-password").value, p2 = $("r-conferma").value;
  const esito = $("r-esito");
  esito.hidden = false;
  if (attiva && (p1 || !stato.info.rete.password)) {
    if (p1.length < 8) { esito.textContent = T("La password deve avere almeno 8 caratteri."); return; }
    if (p1 !== p2) { esito.textContent = T("Le due password non coincidono."); return; }
  }
  try {
    const r = await invia("/api/rete", { attiva, password: attiva ? p1 : "" });
    if (!r.ok) { esito.textContent = r.errore; return; }
    $("r-password").value = $("r-conferma").value = "";
    stato.info.rete = r;
    mostraRete(r);
    esito.textContent = r.riavvio
      ? T("Salvato. Chiudi e riapri Labellula (doppio clic sull'icona) per applicare. La prima volta il firewall può chiedere il permesso: consentilo sulle reti private.")
      : T("Salvato.");
  } catch (e) { esito.textContent = T("Errore:") + " " + e.message; }
}
$("r-attiva").addEventListener("click", () => impostaRete(true));
$("r-disattiva").addEventListener("click", () => impostaRete(false));
function apriAiuto() { document.querySelectorAll("dialog[open]").forEach((d) => d.close()); $("a-guida").href = GUIDA; $("d-aiuto").showModal(); }
$("b-aiuto").addEventListener("click", apriAiuto);
document.addEventListener("click", (e) => { if (e.target.closest(".apri-aiuto")) apriAiuto(); });
$("b-crediti").addEventListener("click", () => {
  const a = $("cr-acquista");
  if (stato.info.url_acquisto) { a.href = stato.info.url_acquisto; a.removeAttribute("aria-disabled"); $("cr-nota").textContent = ""; }
  else { a.removeAttribute("href"); a.setAttribute("aria-disabled", "true"); $("cr-nota").textContent = T("Il servizio è in preparazione: l'acquisto dei codici sarà disponibile sullo shop di ctrlalt.museum."); }
  $("d-crediti").showModal();
});
document.addEventListener("keydown", (e) => {
  if (e.target.matches("input, select, textarea") || document.querySelector("dialog[open]")) return;
  if (e.key === "/" ) { e.preventDefault(); $("q").focus(); return; }
  if (e.key === "?") { apriAiuto(); return; }
  if ($("pannello").hidden) return;
  if (e.key === "Escape") chiudi();
  if (e.key === "ArrowLeft") $("prec").click();
  if (e.key === "ArrowRight") $("succ").click();
});
window.addEventListener("popstate", () => { stato.simili = null; stato.filtri = daHash(); scriviForm(stato.filtri); cerca(true); });

// ------------------------------------------------------------------ lingua
(() => {
  const sel = $("lingua");
  for (const [c, nome] of Object.entries(LINGUE)) sel.add(new Option(c.toUpperCase() + " · " + nome, c));
  sel.value = LINGUA;
  sel.addEventListener("change", async () => {
    const l = sel.value;
    try { localStorage.setItem("labellula.lingua", l); } catch { /* niente */ }
    if (stato.info.rete && stato.info.rete.da_questo_computer) {
      try {
        await invia("/api/lingua", { lingua: l });
        alert(T("Le nuove schede saranno scritte in {l}. Per riscrivere quelle esistenti: «＋ Descrivi foto» › «Aggiorna».", { l: LINGUE[l] }));
      } catch { /* la lingua della pagina cambia comunque */ }
    }
    location.reload();
  });
  traduciPagina();
})();

(async () => {
  try { await caricaFiltri(); } catch (e) { $("stato").textContent = T("Errore:") + " " + e.message; return; }
  stato.filtri = daHash();
  scriviForm(stato.filtri);
  mostraUltime();
  cerca(true);
  seguiLavoro();
})();
