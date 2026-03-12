# PreciAgro MVP — Week 1

AI-powered agricultural intelligence for smallholder farmers.

## Core loop

Farmer photo + GPS → Context assembly → Claude API → Structured diagnosis

## Setup

```bash
cp .env.example .env
# Fill in your keys
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

## Test

```bash
python test_e2e.py
```
