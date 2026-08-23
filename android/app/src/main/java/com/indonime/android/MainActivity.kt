package com.indonime.android

import android.annotation.SuppressLint
import android.os.Bundle
import android.webkit.*
import android.view.View
import android.view.WindowManager
import android.graphics.Color
import androidx.appcompat.app.AppCompatActivity

class MainActivity : AppCompatActivity() {

    private lateinit var webView: WebView

    // Server URL — change to your computer's IP for physical device
    // Emulator: 10.0.2.2 = host localhost
    // Physical device: use your computer's local IP (e.g., 192.168.1.x)
    private val SERVER_URL = "http://10.0.2.2:8756"

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Fullscreen immersive
        window.decorView.systemUiVisibility = (
            View.SYSTEM_UI_FLAG_LAYOUT_STABLE
            or View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
        )
        window.statusBarColor = Color.parseColor("#0F0F23")
        window.navigationBarColor = Color.parseColor("#0F0F23")

        webView = WebView(this)
        setContentView(webView)

        // WebView settings
        webView.settings.apply {
            javaScriptEnabled = true
            domStorageEnabled = true
            mediaPlaybackRequiresUserGesture = false
            allowContentAccess = true
            loadWithOverviewMode = true
            useWideViewPort = true
            builtInZoomControls = false
            displayZoomControls = false
            cacheMode = WebSettings.LOAD_DEFAULT
            mixedContentMode = WebSettings.MIXED_CONTENT_NEVER_ALLOW
            userAgentString = webView.settings.userAgentString.replace(
                "wv", "" // Remove "WebView" identifier for better site compatibility
            )
        }

        // Chrome client for better JS support
        webView.webChromeClient = object : WebChromeClient() {
            override fun onProgressChanged(view: WebView?, newProgress: Int) {
                super.onProgressChanged(view, newProgress)
                // Could show loading indicator here
            }
        }

        // WebView client
        webView.webViewClient = object : WebViewClient() {
            override fun shouldOverrideUrlLoading(view: WebView?, request: WebResourceRequest?): Boolean {
                // Keep all navigation inside WebView
                return false
            }

            override fun onReceivedError(view: WebView?, request: WebResourceRequest?, error: WebResourceError?) {
                super.onReceivedError(view, request, error)
                // Show error page
                view?.loadData(
                    errorPage(),
                    "text/html",
                    "UTF-8"
                )
            }
        }

        // Load the React UI
        webView.loadUrl(SERVER_URL)
    }

    override fun onBackPressed() {
        if (webView.canGoBack()) {
            webView.goBack()
        } else {
            super.onBackPressed()
        }
    }

    override fun onResume() {
        super.onResume()
        webView.onResume()
    }

    override fun onPause() {
        super.onPause()
        webView.onPause()
    }

    override fun onDestroy() {
        webView.destroy()
        super.onDestroy()
    }

    private fun errorPage(): String = """
        <!DOCTYPE html>
        <html>
        <head><meta name="viewport" content="width=device-width, initial-scale=1"></head>
        <body style="background:#0F0F23;color:#F4F4FF;font-family:system-ui;display:flex;align-items:center;justify-content:center;height:100vh;margin:0;text-align:center">
            <div>
                <p style="font-size:48px">⚠️</p>
                <h2 style="color:#F4F4FF">Server tidak ditemukan</h2>
                <p style="color:#A9A6C9">Pastikan Python server jalan di komputer kamu:</p>
                <code style="background:#1E1C35;padding:12px;border-radius:8px;color:#A78BFA;display:inline-block;margin-top:8px">python -m indonime.app</code>
                <p style="color:#6E6B8F;margin-top:16px;font-size:13px">IP server: $SERVER_URL</p>
            </div>
        </body>
        </html>
    """.trimIndent()
}
