"""Optional: keeps the website fed without Claude. Run on the Windows PC: python agent.py"""
import os, time, core
last_learn = 0.0
while True:
    if time.time() - last_learn > float(os.getenv("LEARN_HOURS", "24")) * 3600:
        try: print("learned folders:", list(core.learn_rules()), flush=True)
        except Exception as e: print("learn error:", e, flush=True)
        last_learn = time.time()
    try: print(core.sync_inbox(int(os.getenv("SYNC_TOP", "50"))), flush=True)
    except Exception as e: print("sync error:", e, flush=True)
    time.sleep(int(os.getenv("SYNC_SECONDS", "60")))
