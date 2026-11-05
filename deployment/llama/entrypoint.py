import os,sys
if len(os.getenv("LLAMA_API_KEY",""))<32:raise SystemExit("Run the host AI installer to generate a private local runtime key.")
os.execv("/usr/local/bin/llama-server",["llama-server",*sys.argv[1:]])
