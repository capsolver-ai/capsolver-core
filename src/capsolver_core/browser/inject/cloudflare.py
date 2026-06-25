"""In-page Cloudflare Turnstile scripts (ported from the Node SDK's cloudflare.inject.ts).

Self-contained JS snippets — see recaptcha.py for the pattern.
"""

# ── Cheap presence check ──────────────────────────────────────────

DETECT_CLOUDFLARE_JS = """
() => {
    // Match Cloudflare-specific markers only. A bare [data-sitekey] is NOT
    // Cloudflare-exclusive (reCAPTCHA/hCaptcha use it too) and would cause a
    // reCAPTCHA page to be mis-detected as Cloudflare.
    return !!document.querySelector(
        'input[name="cf-turnstile-response"], .cf-turnstile, iframe[src*="challenges.cloudflare.com"]'
    );
}
"""

# ── Extract info for Cloudflare Turnstile widgets on the page ─────

GET_CLOUDFLARE_INFOS_JS = """
() => {
    // Only consider Cloudflare-specific containers — never a bare
    // [data-sitekey], which would grab a reCAPTCHA/hCaptcha sitekey and
    // build an invalid Turnstile task.
    const widget =
        document.querySelector('.cf-turnstile[data-sitekey]') ||
        document.querySelector('.cf-turnstile');

    let websiteKey = widget ? widget.getAttribute('data-sitekey') : null;
    let action = widget ? widget.getAttribute('data-action') : null;
    let cdata = widget ? widget.getAttribute('data-cdata') : null;

    // Fall back to the widget iframe's query string.
    if (!websiteKey) {
        const iframe = document.querySelector('iframe[src*="challenges.cloudflare.com"]');
        if (iframe && iframe.src) {
            const params = new URL(iframe.src.replace('#', '?')).searchParams;
            websiteKey = params.get('sitekey');
            action = action || params.get('action');
            cdata = cdata || params.get('cData');
        }
    }

    // Identify a container for fill / autofill.
    const input = document.querySelector('input[name="cf-turnstile-response"]');
    const container = (input ? input.parentElement : widget) || null;
    if (container && !container.id) container.id = 'cloudflare-container-' + Date.now();

    if (!websiteKey) return [];
    return [{ websiteKey, action, cdata, containerId: container ? container.id : null }];
}
"""

# ── Write the token back into the hidden input ────────────────────

FILL_CLOUDFLARE_JS = """
(args) => {
    const scope = args.containerId ? document.getElementById(args.containerId) : document;
    const input =
        (scope ? scope.querySelector('input[name="cf-turnstile-response"]') : null) ||
        document.querySelector('input[name="cf-turnstile-response"]');
    if (!input) return false;
    input.value = args.token;
    return true;
}
"""
