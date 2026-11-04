"""Browser-test helper for the in-page confirmation (frontend/static/js/confirm_dialog.js), which replaced the native
window.confirm() on 2026-10-14: click the button that asks, then answer the dialog with this."""

from __future__ import annotations


async def answer_confirm(page, accept: bool = True) -> str:
    """Wait for the confirmation, press Continue/Delete (or Cancel), wait for it to close; returns its message."""
    dialog = page.locator(".confirm-dialog")
    await dialog.wait_for()
    message = (await dialog.locator("p").text_content()) or ""
    await dialog.locator('[data-confirm="ok"]' if accept else '[data-confirm="cancel"]').click()
    await dialog.wait_for(state="detached")
    return message
