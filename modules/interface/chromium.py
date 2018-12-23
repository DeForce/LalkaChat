from cefpython3 import cefpython
import platform
import wx

DEFAULT_TIMER_MILLIS = 10

class ChromeWindow(wx.Window):
    """
    Standalone CEF component. The class provides facilites for interacting
    with wx message loop
    """

    def __init__(self, parent, url="", use_timer=True,
                 timer_millis=DEFAULT_TIMER_MILLIS, browser_settings=None,
                 size=(-1, -1), *args, **kwargs):
        wx.Window.__init__(self, parent, id=wx.ID_ANY, size=size,
                           *args, **kwargs)

        # This timer is not used anymore, but creating it for backwards
        # compatibility. In one of external projects ChromeWindow.timer.Stop()
        # is being called during browser destruction.
        self.timer = wx.Timer()

        # On Linux absolute file urls need to start with "file://"
        # otherwise a path of "/home/some" is converted to "http://home/some".
        if platform.system() in ["Linux", "Darwin"]:
            if url.startswith("/"):
                url = "file://" + url
        self.url = url

        window_info = cefpython.WindowInfo()
        window_info.SetAsChild(self.GetHandle())

        if not browser_settings:
            browser_settings = {}

        self.browser = cefpython.CreateBrowserSync(window_info,
                                                   browserSettings=browser_settings, navigateUrl=url)

        if platform.system() == "Windows":
            self.Bind(wx.EVT_SET_FOCUS, self.OnSetFocus)
            self.Bind(wx.EVT_SIZE, self.OnSize)

        self._useTimer = use_timer
        self.Bind(wx.EVT_IDLE, self.OnIdle)

        self.Bind(wx.EVT_CLOSE, self.OnClose)

    def OnClose(self, event):
        if not self._useTimer:
            try:
                self.Unbind(wx.EVT_IDLE)
            except:
                # Calling Unbind() may cause problems on Windows 8:
                # https://groups.google.com/d/topic/cefpython/iXE7e1ekArI/discussion
                # (it was causing problems in __del__, this might not
                #  be true anymore in OnClose, but still let's make sure)
                pass
        self.browser.ParentWindowWillClose()

    def OnIdle(self, event):
        """Service CEF message loop when useTimer is False"""
        cefpython.MessageLoopWork()
        event.Skip()

    def OnSetFocus(self, event):
        """OS_WIN only."""
        cefpython.WindowUtils.OnSetFocus(self.GetHandle(), 0, 0, 0)
        event.Skip()

    def OnSize(self, event):
        """OS_WIN only. Handle the the size event"""
        cefpython.WindowUtils.OnSize(self.GetHandle(), 0, 0, 0)
        event.Skip()

    def GetBrowser(self):
        """Returns the CEF's browser object"""
        return self.browser

    def LoadUrl(self, url, onLoadStart=None, onLoadEnd=None):
        if onLoadStart or onLoadEnd:
            self.GetBrowser().SetClientHandler(
                CallbackClientHandler(onLoadStart, onLoadEnd))

        browser = self.GetBrowser()
        self.GetBrowser().GetMainFrame().LoadUrl(url)

        # wx.CallLater(100, browser.ReloadIgnoreCache)
        # wx.CallLater(200, browser.GetMainFrame().LoadUrl, url)


class ChromeCtrl(wx.Panel):
    def __init__(self, parent, url="", useTimer=True,
                 timerMillis=DEFAULT_TIMER_MILLIS,
                 browserSettings=None, hasNavBar=True,
                 *args, **kwargs):
        # You also have to set the wx.WANTS_CHARS style for
        # all parent panels/controls, if it's deeply embedded.
        wx.Panel.__init__(self, parent, style=wx.WANTS_CHARS, *args, **kwargs)

        self.chromeWindow = ChromeWindow(self, url=str(url), use_timer=useTimer,
                                         browser_settings=browserSettings)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.navigationBar = None

        sizer.Add(self.chromeWindow, 1, wx.EXPAND, 0)

        self.SetSizer(sizer)
        self.Fit()

        ch = DefaultClientHandler(self)
        self.SetClientHandler(ch)
        if self.navigationBar:
            self.UpdateButtonsState()

    def _InitEventHandlers(self):
        self.navigationBar.backBtn.Bind(wx.EVT_BUTTON, self.OnLeft)
        self.navigationBar.forwardBtn.Bind(wx.EVT_BUTTON, self.OnRight)
        self.navigationBar.reloadBtn.Bind(wx.EVT_BUTTON, self.OnReload)

    def SetClientHandler(self, handler):
        self.chromeWindow.GetBrowser().SetClientHandler(handler)

    def OnLeft(self, event):
        if self.chromeWindow.GetBrowser().CanGoBack():
            self.chromeWindow.GetBrowser().GoBack()
        self.UpdateButtonsState()
        self.chromeWindow.GetBrowser().SetFocus(True)

    def OnRight(self, event):
        if self.chromeWindow.GetBrowser().CanGoForward():
            self.chromeWindow.GetBrowser().GoForward()
        self.UpdateButtonsState()
        self.chromeWindow.GetBrowser().SetFocus(True)

    def OnReload(self, event):
        self.chromeWindow.GetBrowser().Reload()
        self.UpdateButtonsState()
        self.chromeWindow.GetBrowser().SetFocus(True)

    def UpdateButtonsState(self):
        self.navigationBar.backBtn.Enable(
            self.chromeWindow.GetBrowser().CanGoBack())
        self.navigationBar.forwardBtn.Enable(
            self.chromeWindow.GetBrowser().CanGoForward())

    def OnLoadStart(self, browser, frame):
        if self.navigationBar:
            self.UpdateButtonsState()
            self.navigationBar.GetUrlCtrl().SetValue(
                browser.GetMainFrame().GetUrl())
            self.navigationBar.AddToHistory(browser.GetMainFrame().GetUrl())

    def OnLoadEnd(self, browser, frame, http_code):
        if self.navigationBar:
            # In CEF 3 the CanGoBack() and CanGoForward() methods
            # sometimes do work, sometimes do not, when called from
            # the OnLoadStart event. That's why we're calling it again
            # here. This is still not perfect as OnLoadEnd() is not
            # guaranteed to get called for all types of pages. See the
            # cefpython documentation:
            # https://code.google.com/p/cefpython/wiki/LoadHandler
            # OnDomReady() would be perfect, but is still not implemented.
            # Another option is to implement our own browser state
            # using the OnLoadStart and OnLoadEnd callbacks.
            self.UpdateButtonsState()


class DefaultClientHandler(object):
    def __init__(self, parentCtrl):
        self.parentCtrl = parentCtrl

    def OnLoadStart(self, browser, frame):
        self.parentCtrl.OnLoadStart(browser, frame)

    def OnLoadEnd(self, browser, frame, http_code=None):
        self.parentCtrl.OnLoadEnd(browser, frame, http_code=http_code)

    def OnLoadError(self, browser, frame, errorCode, errorText, failedUrl):
        pass


class CallbackClientHandler(object):
    def __init__(self, onLoadStart=None, onLoadEnd=None):
        self._onLoadStart = onLoadStart
        self._onLoadEnd = onLoadEnd

    def OnLoadStart(self, browser, frame):
        if self._onLoadStart and frame.GetUrl() != "about:blank":
            self._onLoadStart(browser, frame)

    def OnLoadEnd(self, browser, frame, httpStatusCode):
        if self._onLoadEnd and frame.GetUrl() != "about:blank":
            self._onLoadEnd(browser, frame, httpStatusCode)

    def OnLoadError(self, browser, frame, errorCode, errorText, failedUrl):
        pass


def Initialize(settings=None, debug=False):
    """Initializes CEF, We should do it before initializing wx
       If no settings passed a default is used
    """
    switches = {}
    global g_settings
    if not settings:
        settings = {}

    if "log_severity" not in settings:
        settings["log_severity"] = cefpython.LOGSEVERITY_ERROR
    if "log_file" not in settings:
        settings["log_file"] = ""

    if "browser_subprocess_path" not in settings:
        settings["browser_subprocess_path"] = \
            "%s/%s" % (cefpython.GetModuleDirectory(), "subprocess")

    if debug:
        settings["debug"] = True  # cefpython messages in console and log_file
        settings["log_severity"] = cefpython.LOGSEVERITY_VERBOSE
        settings["log_file"] = "debug.log"  # Set to "" to disable.

    g_settings = settings
    cefpython.Initialize(settings, switches)


def Shutdown():
    """Shuts down CEF, should be called by app exiting code"""
    cefpython.Shutdown()
