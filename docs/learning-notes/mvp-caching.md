# MVP caching: the simple mental model

A cache is a labeled storage box for work the app has already completed. Before doing the work again, the app checks the label. If every important input on the label is the same, it can reuse the result. If one important input changed, it builds a fresh result.

## The three layers

### 1. Persistent public-standard source

The local SQLite corpus is like the app's reviewed reference bookshelf. It survives a browser restart. The Streamlit screen opens it read-only, so displaying a review cannot silently add or change standards.

### 2. Derived review-package cache

Streamlit reruns the Python script when a user interacts with a widget. Building all requirement mappings, controls, and remediation plans on every rerun repeats the same deterministic work. `st.cache_data` keeps a serialized copy and returns a fresh copy to the caller.

Its key covers:

- the public document's content hash;
- parsed standard identity and requirements;
- the SQLite file's size and modification time;
- a cache-policy version controlled by the project.

The cache holds at most 32 entries. Changing any key input causes a miss and a safe rebuild.

### 3. Exact model-result session cache

An optional external draft can cost money and add latency. After a user explicitly approves a send, the app first checks this browser session for the exact validated result. The key includes the provider, model, full structured request, prompt, public excerpt, and output-schema version. The key itself is a SHA-256 fingerprint, so those inputs are not exposed in cache metrics.

The result is not shared between users and disappears with the browser session or the Clear action. An exact hit still requires the approval checkbox and Send click; it then reports that the provider was not called.

## Why there is no semantic cache yet

A semantic cache tries to reuse an answer for a merely similar question. That is useful in some chatbots, but risky for compliance work: a changed Functional Entity, version, effective date, or requirement can change the correct guidance. Exact matching is easier to test, explain, and audit.

## What the cache never stores

- API keys or provider objects;
- human approval as a reusable permission;
- raw uploaded PDF bytes;
- confidential evidence or live IT/OT data;
- compliance decisions.

## How to verify it

The automated cache-policy tests verify that changing the model, prompt, source, document, or corpus revision produces a new key. In the app, sending the exact same approved model request twice in one session displays a message that the validated result was reused and no external call was made. Package caching stays transparent because it is an implementation detail rather than a review task.
