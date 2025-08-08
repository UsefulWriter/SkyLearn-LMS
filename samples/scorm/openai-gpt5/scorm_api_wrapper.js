/* Minimal SCORM 1.2 API Wrapper
 * - Finds window.API
 * - Exposes doInitialize, doGetValue, doSetValue, doCommit, doFinish
 * - Gracefully no-ops if API not available (e.g., local preview)
 */
(function (global) {
  var debug = false;

  function log() {
    if (!debug) return;
    try { console.log.apply(console, arguments); } catch (e) {}
  }

  function findAPI(win) {
    var findTries = 0;
    var maxTries = 7; // limit parent traversal
    while ((win.API == null) && (win.parent != null) && (win.parent !== win) && (findTries <= maxTries)) {
      findTries += 1;
      win = win.parent;
    }
    return win.API || null;
  }

  function getAPI() {
    var api = null;
    try {
      // Try current window and parents
      api = global.API || findAPI(global);
      // Try opener if present
      if (!api && global.opener && !global.opener.closed) {
        api = global.opener.API || findAPI(global.opener);
      }
    } catch (e) {
      // ignore cross-origin errors
    }
    if (!api) log('[SCORM] API not found');
    return api;
  }

  var API = null;
  var initialized = false;
  var terminated = false;

  var APIWrapper = {
    doInitialize: function () {
      if (initialized) return true;
      API = getAPI();
      if (!API) {
        log('[SCORM] No API; running in preview mode (no-op).');
        initialized = true;
        return true;
      }
      var res = API.LMSInitialize ? API.LMSInitialize('') : 'false';
      initialized = (res === 'true');
      log('[SCORM] Initialize:', initialized);
      return initialized;
    },

    doGetValue: function (name) {
      if (!initialized) this.doInitialize();
      if (!API) return '';
      var val = API.LMSGetValue ? API.LMSGetValue(name) : '';
      log('[SCORM] GetValue', name, '=>', val);
      return val;
    },

    doSetValue: function (name, value) {
      if (!initialized) this.doInitialize();
      if (!API) return true;
      var res = API.LMSSetValue ? API.LMSSetValue(name, String(value)) : 'false';
      var ok = (res === 'true');
      log('[SCORM] SetValue', name, value, '=>', ok);
      return ok;
    },

    doCommit: function () {
      if (!initialized) this.doInitialize();
      if (!API) return true;
      var res = API.LMSCommit ? API.LMSCommit('') : 'false';
      var ok = (res === 'true');
      log('[SCORM] Commit =>', ok);
      return ok;
    },

    doFinish: function () {
      if (terminated) return true;
      if (!API) {
        terminated = true;
        return true;
      }
      var res = API.LMSFinish ? API.LMSFinish('') : 'false';
      var ok = (res === 'true');
      terminated = ok;
      log('[SCORM] Finish =>', ok);
      return ok;
    },

    getLastError: function () {
      return API && API.LMSGetLastError ? API.LMSGetLastError() : '0';
    },

    getErrorString: function (code) {
      return API && API.LMSGetErrorString ? API.LMSGetErrorString(code) : '';
    },

    getDiagnostic: function (code) {
      return API && API.LMSGetDiagnostic ? API.LMSGetDiagnostic(code) : '';
    }
  };

  global.APIWrapper = APIWrapper;
})(window);
