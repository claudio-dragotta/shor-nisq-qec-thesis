# Interactive demo → moved to its own repository

The interactive demo of Shor's algorithm (circuit + per-qubit Bloch spheres, step-by-step, with
statistical execution over many iterations) now lives in a **dedicated, deploy-ready repository**:

- **Live:** <https://shor-demo-6knp.onrender.com>
- **Source:** <https://github.com/claudio-dragotta/shor-demo> (FastAPI + Qiskit, deployed on Render)

It was moved out of this monorepo so it can be iterated and redeployed independently. The earlier
Streamlit version of the demo remains in this repository's git history.
