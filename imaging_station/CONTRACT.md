# Imaging station MVP contract

Python 3.12 standard library, local-only server at `127.0.0.1:8830`. No external web assets.
NAS mounted at `/mnt/xyzbox-nas`; image repository `/mnt/xyzbox-nas/XYZBoxImages`.
State and job logs in `/var/lib/xyzbox-imager`. Code in `/opt/xyzbox-imager`.

## HTTP API (server.py owned by root agent)

- GET `/api/state`: `{station:{hostname,repository,repository_online,busy},drives:[...],images:[...],jobs:[...]}`.
- POST `/api/jobs`: JSON `{operation:'capture'|'restore',device:'/dev/sda',serial:'native SSD serial',image_id:'slug',label:'human label',profile:'seavo-sv3-piper-rt',confirm_serial:'native SSD serial'}`. `image_id` supplied only for restore. Returns `{job:{...}}` (202) or `{error:'...'}` (400/409).
- All POSTs require `Content-Type: application/json` and `X-XYZBox-Request: 1`.
- Drive: `{device,model,serial,size_bytes,transport,mountpoints:[],eligible,reason}`. Internal/system disks visible but not selectable. Native NVMe serial required for ASMedia USB bridge; bridge serial is insufficient.
- Image: `{id,label,project,project_name,profile,version,profile_supported,created_at,status,minimum_disk_bytes,size_bytes,source:{model,serial},software:{...},verified}`. Only verified `ready` images with a validated `profile_supported` adapter are restorable; `customer_ready` is a separate human release assertion. Legacy Yikai images infer project ownership from their existing profile without rewriting NAS files.
- Job: `{id,operation,status:'queued'|'running'|'succeeded'|'failed'|'interrupted',phase,progress:null|0..100,device,serial,image_id,started_at,finished_at,error,log:[]}`.

Times ISO UTC; UI displays Asia/Shanghai. Poll every 2s. Escape all text, no arbitrary shell UI.
`--preview-state SNAPSHOT_JSON` serves a clearly labelled historical read-only view. It must never initialize Engine or accept POST operations.

## core.py (backend agent)

`Engine(repository: str, state_dir: str)`; methods:
- `drives() -> list[dict]`
- `images() -> list[dict]`
- `jobs() -> list[dict]`
- `repository_online() -> bool` (must verify actual CIFS mount, never local fallback)
- `submit(payload: dict) -> dict` starts background single job, rejects concurrent jobs, fresh identity check and explicit serial confirmation.

All imaging requires root, external USB, unmounted partitions, native disk identity, complete system-disk ancestor exclusion (root/home/boot/EFI/swap), and source/target identity recheck before each mutation. Task inhibitor blocks sleep without global power changes. Capture uses Partclone used blocks -> zstd, GPT metadata, SHA256 + decompression + partclone.chkimg before atomic publication. Restore verifies complete image before disk mutation, minimum actual bytes, GPT and partitions, read-back/FS checks, then identity finalizer. No arbitrary commands from requests. Capture source must be block RO during imaging and restored to prior RO state afterwards. Failures never produce ready images. Incomplete jobs become interrupted on restart.

UI agent owns only `static/`; backend agent owns `core.py`, `test_core.py`. Root owns server/deployment, live disk/NAS, customer customization, and integration.
