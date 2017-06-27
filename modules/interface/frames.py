import wx
try:
    from cefpython3.wx import chromectrl as browser
    HAS_CHROME = True
except ImportError:
    from wx import html2 as browser


class OAuthBrowser(wx.Frame):
    def __init__(self, parent, url):
        wx.Frame.__init__(self, parent)
        self.sizer = wx.BoxSizer(wx.HORIZONTAL)

        if HAS_CHROME:
            self.browser = browser.ChromeWindow(self, url)
        else:
            self.browser = browser.WebView.New(parent=self, url=url, name='LalkaWebViewGui')

        self.sizer.Add(self.browser, 1, wx.EXPAND)

        self.SetSizer(self.sizer)
        self.Show()
        self.SetFocus()
