'use strict';

(() => {
  const $ = id => document.getElementById(id);
  const state = { data: null, operation: 'capture', driveKey: null, imageId: null, submitting: false, connected: false, logOpen: new Set(), signature: '' };
  const statusNames = { queued: '排队中', running: '执行中', succeeded: '已完成', failed: '失败', interrupted: '已中断', ready: '技术校验通过', draft: '草稿', verifying: '校验中', capturing: '备份中', incomplete: '未完成' };
  const phaseNames = { queued: '等待执行', starting: '准备任务', preparing: '准备任务', identify: '核对硬盘身份', inventory: '读取硬盘信息', unmount: '卸载分区', metadata: '保存分区信息', capture: '备份文件系统', imaging: '处理镜像数据', compress: '压缩镜像', verify: '校验镜像', verifying: '校验镜像', restore: '写入目标盘', partition: '恢复分区表', partitions: '恢复分区', checksum: '校验文件摘要', finalize: '初始化系统身份', finalizing: '初始化系统身份', fsck: '检查文件系统', completed: '任务完成', done: '任务完成', failed: '任务失败', interrupted: '任务已中断' };
  Object.assign(phaseNames, {preflight:'核对硬盘与镜像库', 'capture-gpt':'保存分区表', 'capture-partition-1':'备份 EFI 分区', 'capture-partition-2':'备份系统分区', 'verify-image':'校验镜像', published:'镜像已登记', 'verify-before-write':'写入前校验镜像', 'restore-gpt':'恢复分区表', 'restore-partition-1':'写入 EFI 分区', 'restore-partition-2':'写入系统分区', 'read-back-partition-1':'读回校验 EFI 分区', 'read-back-partition-2':'读回校验系统分区', 'finalize-identity-and-boot':'初始化身份与启动文件', verified:'目标盘校验完成', complete:'任务完成'});
  const dateFormatter = new Intl.DateTimeFormat('zh-CN', { timeZone: 'Asia/Shanghai', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
  const fullDateFormatter = new Intl.DateTimeFormat('zh-CN', { timeZone: 'Asia/Shanghai', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });

  function element(tag, className, value) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (value !== undefined && value !== null) node.textContent = String(value);
    return node;
  }
  function displayTime(value, full = false) {
    if (!value) return '—';
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? '时间未知' : (full ? fullDateFormatter : dateFormatter).format(date);
  }
  function bytes(value, detailed = false) {
    const n = Number(value);
    if (!Number.isFinite(n) || n < 0) return '大小未知';
    let unit = 'B'; let amount = n;
    for (const candidate of ['KiB', 'MiB', 'GiB', 'TiB']) {
      if (amount < 1024) break;
      amount /= 1024; unit = candidate;
    }
    const compact = `${amount.toLocaleString('zh-CN', { maximumFractionDigits: unit === 'B' ? 0 : 1 })} ${unit}`;
    return detailed ? `${compact} · ${n.toLocaleString('zh-CN')} 字节` : compact;
  }
  function badge(value, kind = 'neutral') { return element('span', `badge ${kind}`, value); }
  function setDot(id, online) { $(id).className = `status-dot ${online ? 'online' : 'offline'}`; }
  function showMessage(id, message) { $(id).textContent = message; $(id).hidden = !message; }
  function driveKey(drive) { return `${drive.device}\u0000${drive.serial}`; }
  function selectedDrive() { return (state.data?.drives || []).find(d => driveKey(d) === state.driveKey); }
  function selectedImage() { return (state.data?.images || []).find(i => i.id === state.imageId); }
  function restorable(image) { return image.status === 'ready' && Boolean(image.verified); }
  function resetConfirmation() { $('confirm-serial').value = ''; showMessage('form-error', ''); showMessage('form-success', ''); }

  function renderImages() {
    const images = state.data?.images || [];
    const root = $('images'); root.replaceChildren();
    $('image-count').textContent = images.length;
    if (!images.length) {
      root.append(element('p', 'empty-state', state.data?.station?.repository_online ? '镜像库还是空的。\n选择母盘，创建第一个备份。' : 'NAS 未连接，暂时无法读取镜像。'));
      return;
    }
    for (const image of images) {
      const ready = restorable(image);
      const card = element('button', `resource-card${state.imageId === image.id ? ' selected' : ''}`);
      card.type = 'button'; card.disabled = !ready;
      card.setAttribute('aria-pressed', String(state.imageId === image.id));
      const top = element('div', 'resource-top');
      const title = element('div'); title.append(element('strong', 'resource-title', image.label || image.id), element('span', 'resource-subtitle', image.profile || '未标注硬件配置'));
      top.append(title, element('span', ready ? 'selection-dot' : 'locked-icon', ready ? '' : '·'));
      card.append(top);
      const meta = element('div', 'resource-meta');
      meta.append(element('span', '', displayTime(image.created_at, true)), element('span', '', `镜像 ${bytes(image.size_bytes)}`));
      card.append(meta);
      const badges = element('div', 'badges');
      badges.append(badge(ready ? '技术校验通过' : image.status === 'ready' ? '待完整性校验' : statusNames[image.status] || image.status || '状态未知', ready ? 'good' : 'neutral'));
      badges.append(badge(image.customer_ready ? '客户放行已确认' : '待客户放行确认', image.customer_ready ? 'good' : 'neutral'));
      card.append(badges);
      card.append(element('p', 'resource-note', `目标盘至少 ${bytes(image.minimum_disk_bytes)}`));
      const software = image.software || {};
      const softwareSummary = [software.ubuntu ? `Ubuntu ${software.ubuntu}` : '', software.kernel ? `内核 ${software.kernel}` : '', software.sdk ? `SDK ${software.sdk}` : ''].filter(Boolean);
      if (softwareSummary.length) card.append(element('p', 'resource-note', softwareSummary.join(' · ')));
      if (image.source?.model || image.source?.serial) card.append(element('p', 'resource-note', `来源 ${[image.source.model, image.source.serial].filter(Boolean).join(' · ')}`));
      card.addEventListener('click', () => { state.imageId = image.id; showMessage('form-error', ''); renderImages(); renderForm(); });
      root.append(card);
    }
  }

  function renderDrives() {
    const drives = state.data?.drives || [];
    const root = $('drives'); root.replaceChildren();
    $('drive-count').textContent = `${drives.filter(d => d.eligible).length} 可用 / ${drives.length}`;
    if (!drives.length) { root.append(element('p', 'empty-state', '暂未发现硬盘。请连接 USB 硬盘盒。')); return; }
    for (const drive of drives) {
      const selected = state.driveKey === driveKey(drive);
      const card = element('button', `resource-card${selected ? ' selected' : ''}`);
      card.type = 'button'; card.disabled = !drive.eligible;
      card.setAttribute('aria-pressed', String(selected));
      const top = element('div', 'resource-top');
      const title = element('div'); title.append(element('strong', 'resource-title', drive.model || '未知型号硬盘'), element('span', 'resource-subtitle', `${drive.device || '未知设备'} · ${(drive.transport || '未知接口').toUpperCase()}`));
      top.append(title, element('span', drive.eligible ? 'selection-dot' : 'locked-icon', drive.eligible ? '' : '⊘'));
      card.append(top);
      const meta = element('div', 'resource-meta');
      meta.append(element('code', '', `SN ${drive.serial || '未识别原生序列号'}`), element('span', '', bytes(drive.size_bytes)));
      card.append(meta);
      const badges = element('div', 'badges');
      badges.append(badge(drive.eligible ? '可选择' : '已锁定', drive.eligible ? 'good' : 'neutral'));
      if ((drive.mountpoints || []).length) badges.append(badge('分区已挂载', 'warning'));
      card.append(badges);
      if (drive.reason) card.append(element('p', 'resource-note', drive.reason));
      if ((drive.mountpoints || []).length) card.append(element('p', 'resource-note', `挂载 ${drive.mountpoints.join(' · ')}`));
      card.addEventListener('click', () => { if (state.driveKey !== driveKey(drive)) resetConfirmation(); state.driveKey = driveKey(drive); renderDrives(); renderForm(); });
      root.append(card);
    }
  }

  function disabledReason() {
    const station = state.data?.station;
    const drive = selectedDrive(); const image = selectedImage();
    if (!state.connected) return '未连接工作站，等待恢复连接。';
    if (!station?.repository_online) return 'NAS 未连接，无法执行任务。';
    if (state.submitting) return '正在提交任务…';
    if (station.busy) return '当前任务完成后可继续操作。';
    if (!drive || !drive.eligible) return '请选择一块可用的外接硬盘。';
    if (!drive.serial) return '未识别硬盘原生序列号。';
    if (state.operation === 'restore') {
      if (!image || !restorable(image)) return '请选择技术校验通过的镜像。';
      if (drive.serial === image.source?.serial) return '当前连接的是此镜像的母盘，请换入目标盘。';
      if (Number(drive.size_bytes) < Number(image.minimum_disk_bytes)) return '目标盘实际容量不足，请换用更大的硬盘。';
    } else if (!$('image-label').value.trim()) return '请为新镜像填写名称。';
    if ($('confirm-serial').value !== drive.serial) return '请输入与所选硬盘完全一致的序列号。';
    return '';
  }

  function renderForm() {
    const restore = state.operation === 'restore'; const drive = selectedDrive(); const image = selectedImage();
    $('tab-capture').classList.toggle('active', !restore); $('tab-restore').classList.toggle('active', restore);
    $('tab-capture').setAttribute('aria-selected', String(!restore)); $('tab-restore').setAttribute('aria-selected', String(restore));
    $('capture-fields').hidden = restore; $('restore-fields').hidden = !restore;
    $('selected-drive-label').textContent = restore ? '目标盘' : '母盘';
    $('operation-description').textContent = restore ? '将所选系统镜像恢复到外接硬盘，并初始化新设备的系统身份。' : '按文件系统已用数据制作镜像，保存到 NAS，并完成完整性校验。';
    $('selected-drive-name').textContent = drive ? `${drive.model || '未知型号硬盘'} · ${drive.device}` : '请在左侧选择一块硬盘';
    $('selected-drive-serial').textContent = drive?.serial ? `SN ${drive.serial}` : '—';
    $('selected-drive-size').textContent = drive ? bytes(drive.size_bytes, true) : '';
    $('selected-image-name').textContent = image ? image.label || image.id : '请在左侧选择镜像';
    $('selected-image-minimum').textContent = image ? `目标盘至少 ${bytes(image.minimum_disk_bytes, true)}` : '';
    $('submit-label').textContent = state.submitting ? '正在提交…' : restore ? '确认写入目标盘' : '开始备份';
    const reason = disabledReason();
    $('submit-job').disabled = Boolean(reason);
    $('submit-reason').textContent = reason || (restore ? '写入会覆盖所选目标盘上的数据。' : '母盘按只读方式备份。');
  }

  function renderJobs() {
    const jobs = state.data?.jobs || []; const root = $('jobs');
    for (const details of root.querySelectorAll('details[data-job-id]')) {
      if (details.open) state.logOpen.add(details.dataset.jobId); else state.logOpen.delete(details.dataset.jobId);
    }
    const scrolls = new Map([...root.querySelectorAll('pre[data-job-id]')].map(pre => [pre.dataset.jobId, { top: pre.scrollTop, bottom: pre.scrollHeight - pre.clientHeight - pre.scrollTop < 12 }]));
    root.replaceChildren(); $('job-count').textContent = jobs.length;
    if (!jobs.length) { root.append(element('p', 'empty-state', '暂无任务。备份和刷写记录会保存在这里。')); return; }
    for (const job of jobs) {
      const card = element('article', 'job'); const header = element('div', 'job-header'); const title = element('div', 'job-title-group');
      const active = job.status === 'running' || job.status === 'queued';
      title.append(element('strong', 'job-title', job.operation === 'restore' ? '刷写目标盘' : '备份母盘'), badge(statusNames[job.status] || job.status || '未知状态', job.status === 'succeeded' ? 'good' : ['failed', 'interrupted'].includes(job.status) ? 'danger' : active ? 'warning' : 'neutral'));
      header.append(title, element('span', 'job-time', displayTime(job.started_at)));
      card.append(header);
      const meta = element('div', 'job-meta');
      meta.append(element('code', '', `${job.device || '—'} · SN ${job.serial || '—'}`), element('span', '', job.image_id || job.id));
      if (job.finished_at) meta.append(element('span', '', `结束 ${displayTime(job.finished_at)}`));
      card.append(meta);
      const rawProgress = job.progress;
      const progress = rawProgress === null || rawProgress === undefined || !Number.isFinite(Number(rawProgress)) ? null : Math.max(0, Math.min(100, Number(rawProgress)));
      const heading = element('div', 'progress-heading');
      heading.append(element('span', '', phaseNames[job.phase] || job.phase || (active ? '等待进度' : statusNames[job.status] || '—')), element('span', '', progress === null ? (active ? '处理中' : '—') : `阶段 ${progress.toFixed(0)}%`));
      const track = element('div', 'progress-track'); track.setAttribute('role', 'progressbar'); track.setAttribute('aria-label', '任务进度');
      track.setAttribute('aria-valuemin', '0'); track.setAttribute('aria-valuemax', '100');
      if (progress !== null) track.setAttribute('aria-valuenow', String(progress));
      const fill = element('div', `progress-fill ${job.status}${progress === null && active ? ' indeterminate' : ''}`);
      if (progress !== null) fill.style.width = `${progress}%`; else if (!active) fill.style.width = job.status === 'succeeded' ? '100%' : '0%';
      track.append(fill); card.append(heading, track);
      if (job.error) {
        const summary = job.error.startsWith('sgdisk failed') ? '分区表恢复失败；请查看日志，处理后重新刷盘。'
          : job.error.startsWith('python3 failed') ? '系统身份或启动初始化失败；请查看日志，处理后重新刷盘。'
          : job.error.split('\n')[0];
        card.append(element('p', 'job-error', summary));
      }
      const details = element('details'); details.dataset.jobId = job.id; details.open = state.logOpen.has(job.id);
      details.append(element('summary', '', '查看任务日志'));
      const rawLog = Array.isArray(job.log) ? job.log.map(line => typeof line === 'string' ? line : `${displayTime(line.at, true)} ${line.message || ''}`).join('\n') : String(job.log || '');
      const log = rawLog.replace(/\b\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z\b/g, timestamp => `${displayTime(timestamp, true)} 北京时间`);
      const pre = element('pre', '', log || '尚无日志。'); pre.dataset.jobId = job.id;
      details.append(pre); card.append(details); root.append(card);
      const previous = scrolls.get(job.id);
      if (details.open && previous) pre.scrollTop = previous.bottom ? pre.scrollHeight : previous.top;
    }
  }

  function renderState(data) {
    state.data = data; state.connected = true;
    const station = data.station || {};
    $('station-name').textContent = station.hostname || '本地工作站';
    $('nas-title').textContent = station.repository_online ? 'NAS 镜像仓库在线' : 'NAS 镜像仓库离线';
    $('repository-path').textContent = station.repository || 'NAS · XYZBoxImages';
    setDot('connection-dot', true); setDot('footer-dot', true); setDot('nas-dot', Boolean(station.repository_online));
    $('connection-status').textContent = '工作站已连接';
    $('last-updated').textContent = `更新于 ${displayTime(new Date().toISOString())} · 北京时间`;
    $('busy-banner').hidden = !station.busy;
    showMessage('connection-error', '');
    if (state.driveKey && !selectedDrive()) { state.driveKey = null; resetConfirmation(); }
    if (state.imageId && !selectedImage()) state.imageId = null;
    const nextSignature = JSON.stringify([data.drives || [], data.images || []]);
    if (nextSignature !== state.signature) { renderImages(); renderDrives(); state.signature = nextSignature; }
    renderForm(); renderJobs();
  }

  async function readResponse(response) {
    let data;
    try { data = await response.json(); } catch (_) { throw new Error(`工作站返回了无法读取的响应（HTTP ${response.status}）。`); }
    if (!response.ok) throw new Error(data.error || `请求失败（HTTP ${response.status}）。`);
    return data;
  }
  let polling = false;
  async function poll() {
    if (polling) return;
    polling = true;
    const controller = new AbortController(); const timer = setTimeout(() => controller.abort(), 20000);
    try {
      const response = await fetch('/api/state', { cache: 'no-store', signal: controller.signal });
      const data = await readResponse(response);
      if (!data || !data.station || !Array.isArray(data.drives) || !Array.isArray(data.images) || !Array.isArray(data.jobs)) throw new Error('工作站状态数据格式异常。');
      renderState(data);
    } catch (error) {
      state.connected = false;
      setDot('connection-dot', false); setDot('footer-dot', false); setDot('nas-dot', false);
      $('connection-status').textContent = '工作站连接已中断'; $('nas-title').textContent = 'NAS 状态待重新确认';
      showMessage('connection-error', `无法获取最新状态：${error.name === 'AbortError' ? '连接超时。' : error.message} 页面会自动重试；已提交任务的结果以恢复连接后的记录为准。`);
      renderForm();
    } finally { clearTimeout(timer); polling = false; }
  }

  function switchOperation(operation) { if (state.operation === operation) return; state.operation = operation; resetConfirmation(); renderForm(); }
  $('tab-capture').addEventListener('click', () => switchOperation('capture'));
  $('tab-restore').addEventListener('click', () => switchOperation('restore'));
  $('confirm-serial').addEventListener('input', renderForm);
  $('image-label').addEventListener('input', renderForm);
  $('operation-form').addEventListener('submit', async event => {
    event.preventDefault();
    const reason = disabledReason(); if (reason) { showMessage('form-error', reason); return; }
    const drive = selectedDrive(); const image = selectedImage();
    const payload = { operation: state.operation, device: drive.device, serial: drive.serial, confirm_serial: $('confirm-serial').value, profile: state.operation === 'restore' ? image.profile : $('image-profile').value };
    if (state.operation === 'restore') payload.image_id = image.id; else payload.label = $('image-label').value.trim();
    state.submitting = true; showMessage('form-error', ''); showMessage('form-success', ''); renderForm();
    const controller = new AbortController(); const timer = setTimeout(() => controller.abort(), 15000);
    try {
      const response = await fetch('/api/jobs', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-XYZBox-Request': '1' }, body: JSON.stringify(payload), signal: controller.signal });
      const result = await readResponse(response);
      if (!result.job) throw new Error('工作站未返回任务记录，请先刷新任务状态。');
      $('confirm-serial').value = '';
      showMessage('form-success', '任务已提交，请在下方查看进度。');
      await poll();
      $('jobs-title').scrollIntoView({ behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'nearest' });
    } catch (error) {
      showMessage('form-error', `${error.name === 'AbortError' ? '提交请求超时。' : error.message} 若连接中断，请先核对任务记录后再提交。`);
      await poll();
    } finally { clearTimeout(timer); state.submitting = false; renderForm(); }
  });
  poll();
  setInterval(poll, 2000);
})();
