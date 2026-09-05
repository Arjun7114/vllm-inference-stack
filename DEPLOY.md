# Deployment Runbook

How to run the full stack (vLLM model server + FastAPI app layer) with Docker
Compose on a GPU host. This is the orchestrated, production-shaped deployment;
the readiness gate ensures the app never accepts traffic before the model has
finished loading.

> **Host requirement.** This needs a Linux host with an NVIDIA GPU, the NVIDIA
> driver, Docker, and the NVIDIA Container Toolkit — i.e. a machine where you can
> run `docker compose` yourself (e.g. an AWS EC2 GPU instance such as `g5.xlarge`,
> or any bare-metal/VM GPU host). It does **not** run on hosts that disallow
> user-run Docker Compose (e.g. RunPod pods, which run Docker for you).

## 1. Prerequisites on the host

```bash
# NVIDIA driver + Docker must already be present. Verify:
nvidia-smi          # should list the GPU
docker --version    # should print a version

# Install the NVIDIA Container Toolkit so containers can see the GPU
# (skip if the host image already includes it, e.g. AWS Deep Learning AMI):
distribution=$(. /etc/os-release; echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# Verify Docker can see the GPU:
docker run --rm --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi
```

## 2. Get the code

```bash
git clone https://github.com/Arjun7114/vllm-inference-stack.git
cd vllm-inference-stack
```

## 3. Provide secrets

The vLLM service needs a Hugging Face token to pull the (gated) model. Supply it
via the environment — never commit it.

```bash
export HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxxxxx      # your HF read token
export API_KEY=choose-a-strong-key              # app-layer API key
```

Compose reads `${HF_TOKEN}` and `${API_KEY}` from the environment.

## 4. Bring the stack up

```bash
docker compose up --build
```

What happens, in order:

1. Compose pulls the `vllm/vllm-openai` image and builds the app image.
2. The **vllm** service starts and begins downloading + loading the model
   (several minutes). Its healthcheck probes `/health` and stays "starting".
3. The **app** service does **not** start yet — `depends_on: service_healthy`
   holds it back. This is the readiness gate.
4. Once the model is loaded and vLLM reports healthy, the app starts and begins
   accepting traffic.

Watch the logs for the model-load progress and the moment the app comes up.

## 5. Test it

```bash
# From the host (app is published on 8080):
curl http://localhost:8080/health
# -> {"status":"ok","backend":"vllm"}

curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{"messages":[{"role":"user","content":"In one sentence, what is vLLM?"}]}'
```

## 6. Tear down

```bash
docker compose down          # stop and remove the containers
# then STOP/TERMINATE the GPU host so it stops billing
```

## Notes

- The app defaults to `BACKEND=vllm` inside compose and reaches the model server
  at `http://vllm:8000` (compose service DNS).
- Guardrails are passthrough in this compose setup unless a gateway is mounted
  and `GUARDRAILS_GATEWAY_PATH` is set; the app runs correctly either way.
- Ports: app on `8080`, vLLM on `8000`.
