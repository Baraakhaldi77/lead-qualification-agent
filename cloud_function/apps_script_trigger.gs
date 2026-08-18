/**
 * Paste this into Extensions -> Apps Script on your Google Sheet, then
 * wire it as an INSTALLABLE trigger (see walkthrough): function
 * onFormSubmitTrigger, event source "From spreadsheet", event type
 * "On form submit". Fires the instant a lead submits - no polling delay.
 *
 * Fill in CLOUD_FUNCTION_URL after you deploy the Cloud Function.
 */

var CLOUD_FUNCTION_URL = "PASTE_YOUR_CLOUD_FUNCTION_URL_HERE";
var WEBHOOK_SECRET = "PASTE_YOUR_WEBHOOK_SECRET_HERE"; // must match the WEBHOOK_SECRET env var on the Cloud Function - generate your own, don't reuse one from chat history

function onFormSubmitTrigger(e) {
  UrlFetchApp.fetch(CLOUD_FUNCTION_URL, {
    method: "post",
    headers: { "X-Webhook-Secret": WEBHOOK_SECRET },
    muteHttpExceptions: true
  });
}
