# LabSafe Mom Performance Tests

This folder contains protocol files and a small standard-library Python runner
for quick end-to-end website/API performance checks.

## Run

Start the backend and frontend first, then run:

```powershell
cd E:\bme\iGEM\软件\LabSafeMom
python performance_tests\run_performance_tests.py
```

Optional:

```powershell
python performance_tests\run_performance_tests.py --api-url http://localhost:8000/api/v1 --concurrency 2 --repeat 2
```

The runner uploads each `.txt` protocol, triggers analysis, waits for completion,
fetches the report, and prints upload/analyze/total timings plus the final risk.

