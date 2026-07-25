# Demo interattiva della tesi — Streamlit + Qiskit Aer.
# Build context: la ROOT del repo (serve per includere Extra/experiments/).
#   docker build -f Extra/demo/Dockerfile -t tesi-demo .
FROM python:3.12-slim

WORKDIR /app

COPY Extra/demo/requirements.txt Extra/demo/requirements.txt
RUN pip install --no-cache-dir -r Extra/demo/requirements.txt

# Solo ciò che serve alla demo: l'app + la libreria Shor condivisa (M1-M4) + i risultati
# QEC (M5-M8) già calcolati. Non l'intero repo (niente LaTeX/PDF/altri esperimenti).
COPY Extra/demo/ Extra/demo/
COPY Extra/experiments/campagne_classiche_M1-M4/shor_core.py Extra/experiments/campagne_classiche_M1-M4/beauregard.py Extra/experiments/campagne_classiche_M1-M4/
COPY Extra/experiments/M5_repetition_code/*.json Extra/experiments/M5_repetition_code/
COPY Extra/experiments/M6_steane_code/*.json Extra/experiments/M6_steane_code/
COPY Extra/experiments/M6_steane_code/qec_steane.py Extra/experiments/M6_steane_code/
COPY Extra/experiments/M7_surface_code/*.json Extra/experiments/M7_surface_code/
COPY Extra/experiments/M8_shor_logico/*.json Extra/experiments/M8_shor_logico/

WORKDIR /app/Extra/demo

ENV PORT=8501
EXPOSE 8501

# Render (e altre PaaS) iniettano $PORT a runtime; in locale resta 8501 (ENV sopra).
CMD streamlit run app.py --server.port=$PORT --server.address=0.0.0.0 --server.headless=true
