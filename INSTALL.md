# Installation Guide — Pollinations Image Generation Plugin

This guide covers installing the Pollinations image generation plugin for Hermes Agent.

## Prerequisites

- Hermes Agent installed
- Terminal access with permission to edit Hermes config
- Optional: Pollinations account for API key (https://enter.pollinations.ai)

## Step 1: Copy Plugin Files

Place the plugin in your Hermes plugins directory:

```bash
# From the repo root
cp -r plugins/image_gen/pollinations /opt/data/plugins/image_gen/pollinations/
```

Verify files exist:
```bash
ls -la /opt/data/plugins/image_gen/pollinations/
```

Expected output:
```
__init__.py
plugin.yaml
README.md
CHANGELOG.md
INSTALL.md
```

## Step 2: Enable Plugin

Add to Hermes config:

```bash
hermes config set plugins.enabled '["image_gen/pollinations"]'
hermes config set image_gen.provider pollinations
```

## Step 3: Optional API Key

For higher rate limits, add to Hermes `.env`:

```bash
echo "POLLINATIONS_API_KEY=sk_..." >> /opt/data/.env
```

Restart gateway after adding:

```bash
hermes gateway restart
```

## Step 4: Verify Installation

Test that the provider is active:

```bash
hermes config get image_gen.provider
# Expected: pollinations
```

Generate a test image via the `image_generate` tool:

```
Generate a test image: a cute robot chef cooking breakfast
```

If the image saves successfully, the plugin is working.

## Uninstall

```bash
hermes config set plugins.enabled '[]'
hermes config set image_gen.provider none
rm -rf /opt/data/plugins/image_gen/pollinations
hermes gateway restart
```

## Support

- Issues: https://github.com/NousResearch/hermes-agent
- Docs: https://hermes-agent.nousresearch.com/docs/
