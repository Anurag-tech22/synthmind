import json
import urllib.request

print("=========================================================")
print("🚀 SYNTHMIND LIVE DEMO: GOOGLE GEMMA 2 & GOOGLE VEO 3.1")
print("=========================================================")

# 1. Create Research Session
chat_req = urllib.request.Request(
    "http://localhost:8000/api/chat",
    data=json.dumps({"message": "Compare NVIDIA H100 SXM vs Google TPU v5p for 70B parameter LLM training and produce a decision matrix."}).encode(),
    headers={"Content-Type": "application/json"},
)
chat_res = urllib.request.urlopen(chat_req)
chat_data = json.loads(chat_res.read().decode())
session_id = chat_data["session_id"]
print(f"\n[1] Active Research Session: {session_id}")
print(f"[Agent Response Preview]:\n{chat_data['message'][:300]}...\n")

# 2. Run Google Gemma Distillation
print("---------------------------------------------------------")
print("💎 [2] RUNNING GOOGLE GEMMA 2 OPEN FOUNDATION MODEL")
print("---------------------------------------------------------")
gemma_req = urllib.request.Request(
    "http://localhost:8000/api/gemma/distill",
    data=json.dumps({"content": chat_data["message"], "focus": "Hardware & Performance Trade-offs"}).encode(),
    headers={"Content-Type": "application/json"},
)
gemma_res = urllib.request.urlopen(gemma_req)
gemma_data = json.loads(gemma_res.read().decode())
print(f"Model Used: {gemma_data.get('model_used')}")
print(f"Provider:   {gemma_data.get('provider')}")
print(f"\nDistilled Summary:\n{gemma_data.get('summary')}\n")

# 3. Run Google Veo Storyboard Studio
print("---------------------------------------------------------")
print("🎬 [3] RUNNING GOOGLE VEO 3.1 & LYRIA STORYBOARD STUDIO")
print("---------------------------------------------------------")
veo_req = urllib.request.Request(
    "http://localhost:8000/api/veo/storyboard",
    data=json.dumps({"session_id": session_id, "style": "cinematic_tech"}).encode(),
    headers={"Content-Type": "application/json"},
)
veo_res = urllib.request.urlopen(veo_req)
veo_data = json.loads(veo_res.read().decode())
print(f"Video Title:       {veo_data.get('video_title')}")
print(f"Target Veo Model:  {veo_data.get('veo_model')}")
print(f"DeepMind Lyria:    {veo_data.get('lyria_audio_cue')}")
print(f"Veo Master Prompt: {veo_data.get('veo_master_prompt')}\n")

print("Generated Video Scenes:")
for scene in veo_data.get("scenes", []):
    print(f"  ▶ Scene {scene.get('scene_number')}: {scene.get('title')}")
    print(f"    Camera Motion: {scene.get('camera_motion')}")
    print(f"    Visual Prompt: {scene.get('visual_prompt')}")
    print(f"    Voiceover:     {scene.get('voiceover_script')}\n")
