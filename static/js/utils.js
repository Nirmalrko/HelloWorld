function escapeHtml(unsafe) {
    if (typeof unsafe !== 'string') {
        try { return String(unsafe); } catch (e) { return ""; } // Handle non-strings
    }
    return unsafe
         .replace(/&/g, "&amp;")
         .replace(/</g, "&lt;")
         .replace(/>/g, "&gt;")
         .replace(/"/g, "&quot;")
         .replace(/'/g, "&#039;");
}
