"""In-page reCAPTCHA scripts (ported from the Node SDK's recaptcha.inject.ts).

Each constant is a self-contained JavaScript snippet that runs inside the
page via ``page.evaluate``. No imports, no module-scope references — only
the page's ``window``/``document`` and their own arguments.
"""

# ── Cheap presence check ──────────────────────────────────────────

DETECT_RECAPTCHA_JS = """
() => {
    const cfg = window.___grecaptcha_cfg;
    return !!(cfg && cfg.clients && Object.keys(cfg.clients).length > 0);
}
"""

# ── Extract a descriptor for every reCAPTCHA widget on the page ───

GET_RECAPTCHA_INFOS_JS = """
() => {
    function getSaParam() {
        const reCap = document.querySelector('iframe[title="reCAPTCHA"]');
        const src = reCap ? reCap.getAttribute('src') : null;
        if (!src) return null;
        return new URL(src).searchParams.get('sa');
    }

    function getWidgetInfo(widget) {
        const info = {
            captchaType: 'reCaptcha',
            version: 'v2',
            sitekey: null,
            action: null,
            s: null,
            callback: null,
            enterprise: !!(window.grecaptcha && window.grecaptcha.enterprise),
            containerId: null,
            bindedButtonId: null,
            invisible: false,
        };

        // Detect the v3 badge.
        let isBadge = false;
        badge: for (const f in widget) {
            if (typeof widget[f] !== 'object') continue;
            for (const g in widget[f]) {
                if (widget[f][g] && widget[f][g].classList && widget[f][g].classList.contains('grecaptcha-badge')) {
                    isBadge = true;
                    break badge;
                }
            }
        }
        if (isBadge) {
            info.version = 'v3';
            info.captchaType = 'reCaptcha3';
            for (const h in widget) {
                const i = widget[h];
                if (typeof i !== 'object') continue;
                for (const j in i) {
                    if (typeof i[j] !== 'string') continue;
                    if (i[j] === 'fullscreen') {
                        info.version = 'v2';
                        info.captchaType = 'reCaptcha';
                    }
                }
            }
        }

        // Find the container element id.
        let candidate = null;
        for (const k in widget) {
            if (widget[k] && widget[k].nodeType) {
                if (widget[k].id) {
                    info.containerId = widget[k].id;
                } else if (widget[k].dataset && widget[k].dataset.sitekey) {
                    widget[k].id = 'recaptcha-container-' + Date.now();
                    info.containerId = widget[k].id;
                } else if (!candidate) {
                    candidate = widget[k];
                } else if (widget[k].isSameNode(candidate)) {
                    widget[k].id = 'recaptcha-container-' + Date.now();
                    info.containerId = widget[k].id;
                    break;
                }
            }
        }

        // Find sitekey / action / s / callback / bind / size.
        for (const k1 in widget) {
            const obj = widget[k1];
            if (typeof obj !== 'object') continue;
            for (const k2 in obj) {
                if (obj[k2] === null || typeof obj[k2] !== 'object') continue;
                if (obj[k2].sitekey === undefined || obj[k2].action === undefined) continue;
                for (const k3 in obj[k2]) {
                    if (k3 === 'sitekey') info.sitekey = obj[k2][k3];
                    if (k3 === 'action') info.action = obj[k2][k3];
                    if (k3 === 's') info.s = obj[k2][k3];
                    if (k3 === 'callback' || k3 === 'promise-callback') info.callback = obj[k2][k3];
                    if (k3 === 'bind' && obj[k2][k3]) {
                        const bind = obj[k2][k3];
                        if (typeof bind === 'string') {
                            info.bindedButtonId = bind;
                        } else {
                            if (bind.id === undefined) bind.id = 'recaptchaBindedElement' + widget.id;
                            info.bindedButtonId = bind.id;
                        }
                    }
                    if (k3 === 'size' && obj[k2][k3] === 'invisible') info.invisible = true;
                }
            }
        }

        // Stash a function callback under a global key so fill can invoke it.
        if (typeof info.callback === 'function') {
            const callbackKey = 'reCaptchaWidgetCallback' + widget.id;
            window[callbackKey] = info.callback;
            info.callback = callbackKey;
        }

        if (info.captchaType === 'reCaptcha') info.action = getSaParam();

        return info;
    }

    const cfg = window.___grecaptcha_cfg;
    if (!cfg || !cfg.clients) return [];

    const infos = [];
    for (const widgetId in cfg.clients) {
        infos.push(getWidgetInfo(cfg.clients[widgetId]));
    }
    return infos;
}
"""

# ── Write the token back into the response textarea and fire the callback ─

FILL_RECAPTCHA_JS = """
(args) => {
    let textarea = null;
    if (args.containerId) {
        textarea = document.querySelector('#' + args.containerId + ' textarea[name=g-recaptcha-response]');
    }
    if (!textarea) {
        textarea = document.querySelector('textarea[name=g-recaptcha-response]');
    }
    if (textarea) {
        textarea.innerHTML = args.token;
        textarea.value = args.token;
    }

    if (args.callback && typeof window[args.callback] === 'function') {
        try {
            window[args.callback](args.token);
        } catch (e) {
            /* callback threw — token is still set in the textarea */
        }
    }
    return !!textarea;
}
"""
