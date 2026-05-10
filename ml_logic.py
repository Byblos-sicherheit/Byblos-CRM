"""
ml_logic.py – Byblos CRM v2 Machine-Learning-Modul
"""
from __future__ import annotations
import json
import math
from datetime import date, datetime, timedelta
from pathlib import Path
from statistics import mean, stdev
from typing import Dict, List, Optional, Tuple
import pandas as pd
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import LabelEncoder
    SKLEARN_OK = True
except ImportError:
    SKLEARN_OK = False

BASE_DIR   = Path(__file__).resolve().parent
TRAIN_FILE = BASE_DIR / "training_data.json"
_model = _vectorizer = _encoder = None

def load_training_data() -> List[Dict]:
    if TRAIN_FILE.exists():
        try:
            data = json.loads(TRAIN_FILE.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            return []
    return _default_training_data()

def _default_training_data() -> List[Dict]:
    return [
        {"text": "Kraftstoff Benzin Diesel Tankstelle", "category": "Kfz-Kosten"},
        {"text": "Fahrzeug PKW Reparatur Werkstatt Inspektion", "category": "Kfz-Kosten"},
        {"text": "Kfz-Versicherung Haftpflicht Fahrzeug", "category": "Versicherungen"},
        {"text": "Büromaterial Papier Drucker Toner Schreibwaren", "category": "Bürokosten"},
        {"text": "Telefon Mobilfunk Internet Handyrechnung", "category": "Kommunikation"},
        {"text": "Miete Büro Lager Gewerbefläche", "category": "Raumkosten"},
        {"text": "Strom Wasser Gas Energie Nebenkosten", "category": "Energie"},
        {"text": "Versicherung Haftpflicht Berufsunfall", "category": "Versicherungen"},
        {"text": "Steuerberater Rechtsanwalt Notarkosten", "category": "Beratungskosten"},
        {"text": "Werbung Marketing Flyer Webseite", "category": "Marketing"},
        {"text": "Fortbildung Schulung Seminar Ausbildung", "category": "Personalentwicklung"},
        {"text": "Löhne Gehälter Lohnsteuer Sozialversicherung", "category": "Personalkosten"},
        {"text": "Uniform Schutzausrüstung Sicherheitskleidung", "category": "Betriebsausstattung"},
        {"text": "Funk Funkgerät Kommunikationsgerät Ausrüstung", "category": "Betriebsausstattung"},
        {"text": "Bank Kontoführung Bankgebühren Kreditkosten", "category": "Finanzkosten"},
        {"text": "Software Lizenz Abonnement IT-Kosten", "category": "IT-Kosten"},
        {"text": "Objektschutz Bewachung Sicherheitsdienst Wachdienst", "category": "Sicherheitsdienstleistung"},
        {"text": "Veranstaltung Event Personenschutz Türsteher", "category": "Veranstaltungsschutz"},
        {"text": "Werkschutz Fabrik Industrieschutz Betriebsschutz", "category": "Werkschutz"},
        {"text": "Revierdienst Streife Patrouille Kontrollgang", "category": "Revierdienst"},
        {"text": "Pforte Empfang Schrankenanlage Zugangskontrolle", "category": "Pfortendienst"},
    ]

def save_training_data(data: List[Dict]) -> None:
    TRAIN_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def train_model():
    if not SKLEARN_OK:
        return None, None, None
    data = load_training_data()
    if not data:
        return None, None, None
    texts  = [str(d.get("text", "")) for d in data]
    labels = [str(d.get("category", "")) for d in data]
    if len(set(labels)) < 2:
        return None, None, None
    vectorizer = TfidfVectorizer(max_features=8000, ngram_range=(1, 2), sublinear_tf=True)
    X = vectorizer.fit_transform(texts)
    encoder = LabelEncoder()
    y = encoder.fit_transform(labels)
    model = LogisticRegression(max_iter=500, C=1.0, solver="lbfgs", multi_class="auto")
    model.fit(X, y)
    return model, vectorizer, encoder

def _ensure_model():
    global _model, _vectorizer, _encoder
    if _model is None:
        _model, _vectorizer, _encoder = train_model()

def _rule_based_category(text: str) -> str:
    t = text.lower()
    rules = [
        (["kraftstoff","benzin","diesel","tank"], "Kfz-Kosten"),
        (["fahrzeug","auto","pkw","kfz","reparatur"], "Kfz-Kosten"),
        (["versicherung","haftpflicht"], "Versicherungen"),
        (["büro","papier","drucker","toner"], "Bürokosten"),
        (["telefon","mobil","internet","handy"], "Kommunikation"),
        (["miete","bürofläche","gewerbefläche"], "Raumkosten"),
        (["strom","wasser","gas","energie"], "Energie"),
        (["steuerberater","rechtsanwalt"], "Beratungskosten"),
        (["werbung","marketing","flyer"], "Marketing"),
        (["schulung","fortbildung","seminar"], "Personalentwicklung"),
        (["lohn","gehalt","lohnsteuer"], "Personalkosten"),
        (["uniform","ausrüstung","funk"], "Betriebsausstattung"),
        (["bank","kontoführung","kredit"], "Finanzkosten"),
        (["software","lizenz","abonnement"], "IT-Kosten"),
    ]
    for keywords, cat in rules:
        if any(k in t for k in keywords):
            return cat
    return "Sonstiges"

def predict_category(text: str) -> Tuple[Optional[str], float]:
    _ensure_model()
    if _model is None or _vectorizer is None or _encoder is None:
        return _rule_based_category(text), 60.0
    try:
        X = _vectorizer.transform([text])
        proba = _model.predict_proba(X)[0]
        idx = int(proba.argmax())
        return str(_encoder.inverse_transform([idx])[0]), float(proba[idx] * 100.0)
    except Exception:
        return _rule_based_category(text), 50.0

def predict_top3(text: str) -> List[Tuple[str, float]]:
    _ensure_model()
    if _model is None or _vectorizer is None or _encoder is None:
        cat = _rule_based_category(text)
        return [(cat, 80.0), ("Sonstiges", 15.0), ("Betriebsausstattung", 5.0)]
    try:
        X = _vectorizer.transform([text])
        proba = _model.predict_proba(X)[0]
        top_idx = proba.argsort()[-3:][::-1]
        return [(str(_encoder.inverse_transform([i])[0]), float(proba[i] * 100)) for i in top_idx]
    except Exception:
        return [(_rule_based_category(text), 60.0)]

def add_training_example(text: str, category: str) -> None:
    data = load_training_data()
    data.append({"text": text, "category": category})
    save_training_data(data)
    global _model, _vectorizer, _encoder
    _model, _vectorizer, _encoder = train_model()

def reset_training_data() -> None:
    if TRAIN_FILE.exists():
        try: TRAIN_FILE.unlink()
        except Exception: pass
    global _model, _vectorizer, _encoder
    _model = _vectorizer = _encoder = None

def score_customer(customer_id: int, df_fn) -> Dict:
    invs = df_fn("SELECT gross_total, paid_amount, status, invoice_date, due_date, paid_date FROM invoices WHERE customer_id=?", (customer_id,))
    if invs.empty:
        return {"score": 50, "grade": "C", "detail": "Keine Rechnungshistorie", "color": "#e67e22", "total_inv": 0, "paid_ok": 0, "overdue": 0, "total_volume": 0.0, "avg_days_late": "k.A."}
    total_inv = len(invs)
    paid_ok   = len(invs[invs["status"] == "bezahlt"])
    overdue   = len(invs[invs["status"] == "ueberfaellig"])
    total_volume = float(invs["gross_total"].sum())
    speed_scores = []
    for _, r in invs[invs["status"] == "bezahlt"].iterrows():
        try:
            due  = date.fromisoformat(str(r["due_date"])[:10])
            paid = date.fromisoformat(str(r["paid_date"])[:10])
            speed_scores.append((paid - due).days)
        except Exception:
            pass
    score = 70
    if speed_scores:
        avg_days = mean(speed_scores)
        if avg_days <= -7:   score += 20
        elif avg_days <= 0:  score += 10
        elif avg_days <= 7:  score += 0
        elif avg_days <= 30: score -= 15
        else:                score -= 30
    if total_inv > 0:
        fail_rate = (overdue) / total_inv
        score -= int(fail_rate * 40)
    if total_volume > 50000: score += 10
    elif total_volume > 20000: score += 5
    elif total_volume > 5000: score += 2
    if total_inv >= 20: score += 10
    elif total_inv >= 10: score += 5
    elif total_inv >= 5: score += 2
    score = max(0, min(100, score))
    if score >= 90:   grade, color = "A+", "#27ae60"
    elif score >= 80: grade, color = "A",  "#27ae60"
    elif score >= 70: grade, color = "B",  "#2ecc71"
    elif score >= 60: grade, color = "C",  "#f39c12"
    elif score >= 45: grade, color = "D",  "#e67e22"
    else:             grade, color = "F",  "#c0392b"
    avg_str = f"{mean(speed_scores):.0f}" if speed_scores else "k.A."
    return {"score": score, "grade": grade, "color": color, "total_inv": total_inv,
            "paid_ok": paid_ok, "overdue": overdue, "total_volume": total_volume,
            "avg_days_late": avg_str,
            "detail": f"{paid_ok}/{total_inv} bezahlt · Ø {avg_str} Tage · {total_volume:,.0f} €"}

def score_all_customers(df_fn) -> pd.DataFrame:
    customers = df_fn("SELECT DISTINCT c.id, c.company FROM customers c JOIN invoices i ON i.customer_id=c.id ORDER BY c.company")
    rows = []
    for _, row in customers.iterrows():
        s = score_customer(int(row["id"]), df_fn)
        rows.append({"Kunde": row["company"], "Score": s["score"], "Note": s["grade"],
                     "Rechnungen": s["total_inv"], "Bezahlt": s["paid_ok"],
                     "Überfällig": s["overdue"], "Volumen_EUR": round(s["total_volume"], 2),
                     "Ø_Tage_Fälligkeit": s["avg_days_late"]})
    return pd.DataFrame(rows).sort_values("Score", ascending=False) if rows else pd.DataFrame()

def detect_invoice_anomalies(df_fn, z_threshold: float = 2.5) -> pd.DataFrame:
    invs = df_fn("SELECT i.id, i.invoice_no, c.company, i.gross_total, i.invoice_date, i.status FROM invoices i JOIN customers c ON c.id=i.customer_id WHERE i.status NOT IN ('storniert')")
    if invs.empty or len(invs) < 5:
        return pd.DataFrame()
    amounts = invs["gross_total"].astype(float).tolist()
    if len(amounts) < 3:
        return pd.DataFrame()
    mu = mean(amounts)
    try: sd = stdev(amounts)
    except Exception: return pd.DataFrame()
    if sd == 0: return pd.DataFrame()
    anomalies = []
    for _, row in invs.iterrows():
        amt = float(row["gross_total"])
        z = abs(amt - mu) / sd
        if z > z_threshold:
            anomalies.append({"Rechnung": row["invoice_no"], "Kunde": row["company"],
                               "Betrag_EUR": round(amt, 2), "Datum": row["invoice_date"],
                               "Status": row["status"], "Z_Score": round(z, 2),
                               "Auffälligkeit": "Sehr hoch" if amt > mu else "Sehr niedrig"})
    return pd.DataFrame(anomalies).sort_values("Z_Score", ascending=False) if anomalies else pd.DataFrame()

def forecast_revenue(df_fn, months_ahead: int = 3) -> List[Dict]:
    hist = df_fn("SELECT substr(invoice_date,1,7) AS monat, SUM(gross_total) AS umsatz FROM invoices WHERE status='bezahlt' AND invoice_date>=date('now','-18 months') GROUP BY substr(invoice_date,1,7) ORDER BY monat")
    if hist.empty or len(hist) < 3:
        return []
    values = hist["umsatz"].astype(float).tolist()
    months = hist["monat"].tolist()
    window = min(3, len(values))
    base = mean(values[-window:])
    recent = values[-6:] if len(values) >= 6 else values
    trend = (recent[-1] - recent[0]) / len(recent) if len(recent) >= 2 else 0.0
    last_month = months[-1]
    try: y, m = int(last_month[:4]), int(last_month[5:7])
    except Exception: return []
    forecasts = []
    for i in range(1, months_ahead + 1):
        m += 1
        if m > 12: m, y = 1, y + 1
        forecasts.append({"monat": f"{y:04d}-{m:02d}", "prognose_eur": round(max(0.0, base + trend * i), 2),
                           "basis_eur": round(base, 2), "trend_eur": round(trend * i, 2)})
    return forecasts

def page_ki_dashboard(df_fn) -> None:
    try:
        import streamlit as st
    except ImportError:
        return
    st.title("🤖 KI-Auswertungen & Prognosen")
    tabs = st.tabs(["🏆 Kunden-Scoring", "⚠️ Anomalien", "📈 Prognose", "🏷️ Kategorisierung", "🧠 Training"])

    with tabs[0]:
        st.subheader("🏆 Kunden-Scoring")
        if st.button("Scoring berechnen", type="primary"):
            with st.spinner("Analysiere..."):
                scores = score_all_customers(df_fn)
            if scores.empty:
                st.info("Noch nicht genug Rechnungsdaten.")
            else:
                c1, c2, c3 = st.columns(3)
                c1.metric("Analysiert", len(scores))
                c2.metric("Ø Score", f"{scores['Score'].mean():.0f}/100")
                c3.metric("Top-Kunde", scores.iloc[0]['Kunde'])
                st.dataframe(scores, use_container_width=True)
                st.bar_chart(scores.set_index("Kunde")["Score"])
        st.subheader("Einzelkunde")
        custs = df_fn("SELECT id, company FROM customers ORDER BY company")
        if not custs.empty:
            sel = st.selectbox("Kunde", custs["company"].tolist())
            cid = int(custs[custs["company"] == sel].iloc[0]["id"])
            s = score_customer(cid, df_fn)
            c1, c2, c3 = st.columns(3)
            c1.metric("Score", f"{s['score']}/100"); c2.metric("Note", s["grade"]); c3.metric("Volumen", f"{s['total_volume']:,.0f} €")
            st.markdown(f'<div style="border-left:4px solid {s["color"]};padding:8px 14px;background:{s["color"]}11;border-radius:4px;">{s["detail"]}</div>', unsafe_allow_html=True)

    with tabs[1]:
        st.subheader("⚠️ Rechnungsanomalien")
        threshold = st.slider("Z-Score Schwellwert", 1.5, 4.0, 2.5, 0.1)
        if st.button("Anomalien suchen"):
            a = detect_invoice_anomalies(df_fn, threshold)
            if a.empty: st.success("✅ Keine Anomalien gefunden.")
            else: st.warning(f"{len(a)} auffällig"); st.dataframe(a, use_container_width=True)

    with tabs[2]:
        st.subheader("📈 Umsatz-Prognose")
        m_ahead = st.slider("Monate voraus", 1, 12, 3)
        fc = forecast_revenue(df_fn, m_ahead)
        if not fc:
            st.info("Mind. 3 Monate Daten nötig.")
        else:
            total_fc = sum(f["prognose_eur"] for f in fc)
            st.metric(f"Prognose {m_ahead} Monate", f"{total_fc:,.2f} €")
            st.dataframe(pd.DataFrame(fc), use_container_width=True)

    with tabs[3]:
        st.subheader("🏷️ BWA-Kategorisierung")
        text = st.text_area("Ausgaben-Beschreibung", "Kraftstoff für Dienstfahrzeug")
        if st.button("Vorschlagen"):
            top3 = predict_top3(text)
            for i, (cat, conf) in enumerate(top3):
                color = ["#27ae60","#f39c12","#e74c3c"][i]
                st.markdown(f'<div style="margin-bottom:6px;"><strong>{i+1}. {cat}</strong> – {conf:.1f}%<br/><div style="background:#2d3142;border-radius:4px;height:8px;"><div style="background:{color};width:{int(conf)}%;height:8px;border-radius:4px;"></div></div></div>', unsafe_allow_html=True)
        correct = st.text_input("Korrekte Kategorie (für Training):")
        if st.button("Trainingsbeispiel speichern") and correct:
            add_training_example(text, correct); st.success("Gespeichert!")

    with tabs[4]:
        st.subheader("🧠 Trainingsdaten")
        data = load_training_data()
        st.metric("Beispiele", len(data))
        if data:
            df2 = pd.DataFrame(data)
            st.dataframe(df2, use_container_width=True, height=250)
            if "category" in df2.columns:
                st.bar_chart(df2["category"].value_counts())
        with st.form("train_form", clear_on_submit=True):
            t = st.text_input("Text"); c = st.text_input("Kategorie")
            if st.form_submit_button("➕ Hinzufügen") and t and c:
                add_training_example(t, c); st.success("Gespeichert!"); st.rerun()
        if st.button("Modell neu trainieren"):
            global _model, _vectorizer, _encoder
            _model, _vectorizer, _encoder = train_model()
            st.success("✅ Trainiert." if _model else "⚠️ Nicht genug Daten.")
        if st.button("Trainings-Daten zurücksetzen"):
            reset_training_data(); st.warning("Zurückgesetzt.")
