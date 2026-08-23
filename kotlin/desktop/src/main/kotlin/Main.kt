@file:OptIn(ExperimentalTextApi::class)

import androidx.compose.foundation.*
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Rect
import androidx.compose.ui.graphics.*
import androidx.compose.ui.graphics.drawscope.Fill
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.foundation.Image
import androidx.compose.ui.draw.blur
import androidx.compose.ui.draw.drawBehind
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.hoverable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsHoveredAsState
import androidx.compose.ui.text.ExperimentalTextApi
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.platform.Font
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.TextUnit
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import javax.imageio.ImageIO
import androidx.compose.ui.unit.sp
import androidx.compose.ui.input.key.Key
import androidx.compose.ui.input.key.KeyEventType
import androidx.compose.ui.input.key.key
import androidx.compose.ui.input.key.type
import androidx.compose.ui.input.key.onPreviewKeyEvent
import androidx.compose.ui.window.Window
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import androidx.compose.ui.window.application
import androidx.compose.ui.window.rememberWindowState
import androidx.compose.ui.awt.SwingPanel
import javafx.application.Platform
import javafx.embed.swing.JFXPanel
import javafx.scene.Scene
import javafx.scene.layout.StackPane
import javafx.scene.media.Media
import javafx.scene.media.MediaPlayer
import javafx.scene.media.MediaView
import io.ktor.client.*
import io.ktor.client.call.*
import io.ktor.client.engine.cio.*
import io.ktor.client.plugins.contentnegotiation.*
import io.ktor.client.request.*
import io.ktor.http.*
import io.ktor.serialization.kotlinx.json.*
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonObject
import java.awt.Desktop
import java.net.ServerSocket
import java.net.URI
import java.util.concurrent.TimeUnit

const val PORT = 8756
const val SERVER = "http://127.0.0.1:$PORT"

val Bg = Color(0xFF0F0F23); val Bg2 = Color(0xFF14132B); val Card = Color(0xFF1E1C35); val Card2 = Color(0xFF262348)
val Fg = Color(0xFFF4F4FF); val FgDim = Color(0xFFA9A6C9); val Muted = Color(0xFF6E6B8F)
val Primary = Color(0xFF7C3AED); val Primary2 = Color(0xFFA78BFA); val Accent = Color(0xFFF43F5E); val Green = Color(0xFF22C55E)
val Border = Color(0x14FFFFFF); val CardR = RoundedCornerShape(16.dp); val SmR = RoundedCornerShape(10.dp); val PillR = RoundedCornerShape(999.dp)
val HeadFont = FontFamily(Font("fonts/outfit-500.ttf", FontWeight.Medium), Font("fonts/outfit-600.ttf", FontWeight.SemiBold), Font("fonts/outfit-700.ttf", FontWeight.Bold), Font("fonts/outfit-800.ttf", FontWeight.ExtraBold))
val BodyFont = FontFamily(Font("fonts/rubik-400.ttf", FontWeight.Normal), Font("fonts/rubik-500.ttf", FontWeight.Medium), Font("fonts/rubik-600.ttf", FontWeight.SemiBold))

@Serializable data class CatResp(val catalog: List<CI>)
@Serializable data class CI(val title: String, val url: String, val image: String? = null, val image_full: String? = null, val genre: List<String>? = null, val ep: String? = null, val synopsis: String? = null)
@Serializable data class HomeResp(val items: List<CI>)
@Serializable data class SearchResp(val results: List<CI>)
@Serializable data class EpsResp(val episodes: List<EP>)
@Serializable data class EP(val title: String, val url: String)
@Serializable data class Opt(val label: String, val url: String)
@Serializable data class OResp(val options: List<Opt>)
@Serializable data class JobResp(val job_id: Int)
@Serializable data class Job(val id: Int, val title: String, val status: String, val done: Long = 0, val total: Long = 0, val dest: String? = null, val size: Long = 0, val error: String? = null)
@Serializable data class JobsResp(val jobs: List<Job>)
val OPT_RES = Regex("^\\[(.+?)\\]\\s*(.*)$")
fun optName(label: String) = OPT_RES.find(label)?.groupValues?.getOrNull(2)?.takeIf { it.isNotBlank() } ?: label
// ponytail: mirror player.py — LOCALAPPDATA (hasil auto-install TUI), scoop, lalu PATH.
// upgrade: bundle mpv via jpackage kalau mau desktop benar-benar mandiri.
fun findMpv(): String? {
  val home = System.getProperty("user.home"); val la = System.getenv("LOCALAPPDATA")
  val cand = listOfNotNull(
    la?.let { "$it/Indonime/mpv/mpv.com" }, la?.let { "$it/Indonime/mpv/mpv.exe" },
    "$home/scoop/apps/mpv/current/mpv.com", "$home/scoop/apps/mpv/current/mpv.exe", "mpv")
  return cand.firstOrNull { c -> try { ProcessBuilder(c, "--version").start().waitFor(5, TimeUnit.SECONDS) } catch (_: Exception) { false } }
}

val http = HttpClient(CIO) { install(ContentNegotiation) { json(kotlinx.serialization.json.Json { ignoreUnknownKeys = true; isLenient = true }) } }
// ponytail: renderer bisa di-override via env buat iGPU lawas/VM; SOFTWARE = low-end mode (animasi berat dimatiin)
val RENDER_API: String = System.getenv("INDONIME_RENDER_API") ?: "DIRECT3D"
val lowEnd: Boolean = RENDER_API == "SOFTWARE"
enum class View { Home, Detail, Player }
var serverProc: Process? = null

fun main() {
    Thread.setDefaultUncaughtExceptionHandler { t, e -> println("KOTLIN-CRASH $t: $e"); e.printStackTrace() }
    // ponytail: default DIRECT3D (GPU); iGPU lawas/VM -> INDONIME_RENDER_API=SOFTWARE; lowEnd = UI tanpa animasi berat buat renderer CPU
    System.setProperty("skiko.renderApi", RENDER_API)
    application {
    Window(onCloseRequest = { serverProc?.destroyForcibly(); exitApplication() }, title = "Indonime", state = rememberWindowState(width = 1080.dp, height = 720.dp)) {
        MaterialTheme(colorScheme = darkColorScheme(background = Bg, onBackground = Fg, surface = Card, onSurface = Fg, primary = Primary, secondary = Primary2, error = Accent), typography = Typography(bodyLarge = TextStyle(fontFamily = BodyFont))) {
            // ponytail: gradient radial full-window mahal di SOFTWARE -> lowEnd skip
            val grad = if (lowEnd) Modifier else Modifier.drawBehind {
                drawRect(Brush.radialGradient(listOf(Primary.copy(0.14f), Color.Transparent), center = Offset(size.width * 0.8f, -size.height * 0.05f), radius = size.width * 0.55f))
                drawRect(Brush.radialGradient(listOf(Accent.copy(0.08f), Color.Transparent), center = Offset(-size.width * 0.08f, size.height * 0.28f), radius = size.width * 0.42f))
            }
            Box(Modifier.fillMaxSize().background(Bg).then(grad)) { Root() }
        }
    }
}
}

@Composable fun Root() {
    var phase by remember { mutableStateOf("boot") }; var view by remember { mutableStateOf(View.Home) }
    var provider by remember { mutableStateOf("otakudesu") }; var providers by remember { mutableStateOf(listOf("otakudesu")) }
    var query by remember { mutableStateOf("") }; var results by remember { mutableStateOf<List<CI>?>(null) }
    var catalog by remember { mutableStateOf<List<CI>?>(null) }; var latest by remember { mutableStateOf<List<CI>?>(null) }
    var featured by remember { mutableStateOf<List<CI>>(emptyList()) }; var anime by remember { mutableStateOf<Pair<CI, List<EP>>?>(null) }
    var stream by remember { mutableStateOf<String?>(null) }; var busy by remember { mutableStateOf("") }; var error by remember { mutableStateOf<String?>(null) }
    var opts by remember { mutableStateOf<Pair<EP, List<Opt>>?>(null) }; var sel by remember { mutableStateOf<Map<String, String>>(emptyMap()) }
    val scope = rememberCoroutineScope()

    LaunchedEffect(Unit) { if (!portOpen(PORT)) { phase = "loading"; launchServer(); var w = 0; while (w < 30000 && !portOpen(PORT)) { Thread.sleep(500); w += 500 } }; phase = "ready" }
    LaunchedEffect(phase) { if (phase != "ready") return@LaunchedEffect; try { val r: JsonObject = http.get("$SERVER/api/providers").body(); providers = r["providers"]?.toString()?.removeSurrounding("[", "]")?.split(",")?.map { it.trim().removeSurrounding("\"") } ?: listOf("otakudesu") } catch (_: Exception) {} }
    LaunchedEffect(provider, phase) { if (phase != "ready") return@LaunchedEffect; results = null; view = View.Home; try { catalog = (http.get("$SERVER/api/catalog?provider=$provider").body() as CatResp).catalog } catch (_: Exception) {}; try { featured = (http.get("$SERVER/api/home?provider=$provider").body() as HomeResp).items } catch (_: Exception) {}; try { latest = (http.get("$SERVER/api/home?provider=$provider").body() as HomeResp).items } catch (_: Exception) {} }

    fun doSearch() { if (query.isBlank()) { results = null; return }; scope.launch { busy = "Mencari…"; try { results = (http.get("$SERVER/api/search?q=${java.net.URLEncoder.encode(query, "UTF-8")}&provider=$provider").body() as SearchResp).results } catch (e: Exception) { error = e.message }; busy = "" } }
    fun pickAnime(item: CI) { scope.launch { busy = "Memuat…"; try { anime = item to (http.get("$SERVER/api/episodes?url=${item.url}&provider=$provider").body() as EpsResp).episodes; view = View.Detail; results = null } catch (e: Exception) { error = e.message }; busy = "" } }
    fun pickEp(ep: EP) { scope.launch { busy = "Mengambil link…"; try { opts = ep to (http.get("$SERVER/api/downloads?url=${java.net.URLEncoder.encode(ep.url, "UTF-8")}&provider=$provider").body() as OResp).options; sel = emptyMap() } catch (e: Exception) { error = e.message }; busy = "" } }
    fun playServer(o: Opt) { scope.launch {
        // Embedded (JavaFX) butuh file utuh: server download ke cache play dulu, kita poll progress.
        busy = "Menyiapkan video…"
        try {
            val jr: JobResp = http.post("$SERVER/api/play-cache") { contentType(ContentType.Application.Json); setBody(mapOf("server_url" to o.url, "label" to o.label)) }.body()
            var j: Job? = null
            while (true) {
                delay(700)
                j = (http.get("$SERVER/api/jobs").body() as JobsResp).jobs.firstOrNull { it.id == jr.job_id } ?: break
                if (j.total > 0) busy = "Menyiapkan video… ${j.done * 100 / j.total}%"
                when (j.status) {
                    "done" -> break
                    "failed" -> { error = j.error ?: "Gagal menyiapkan video"; busy = ""; return@launch }
                    else -> {}
                }
            }
            val dest = j?.dest
            if (dest != null && j?.status == "done") {
                stream = java.io.File(dest).toURI().toString()
                opts = null; view = View.Player
            } else if (error == null) error = "Gagal menyiapkan video"
        } catch (e: Exception) { error = e.message }
        busy = ""
    } }
    fun dlServer(o: Opt, ep: EP) { scope.launch { try { http.post("$SERVER/api/download") { contentType(ContentType.Application.Json); setBody(mapOf("server_url" to o.url, "title" to ep.title)) } } catch (e: Exception) { error = e.message } } }

    when (phase) { "boot","loading" -> BootScreen(); else ->
        Column(Modifier.fillMaxSize()) {
            TopBar(provider, providers, { provider = it }, query, { query = it }, { doSearch() }, { view = View.Home; results = null; query = "" })
            error?.let { ToastBar(it, Accent) { error = null } }; if (busy.isNotEmpty()) ToastBar(busy, Primary)
            when (view) { View.Home -> HomeScreen(catalog, latest, featured, results, query, provider) { pickAnime(it) }; View.Detail -> anime?.let { (item, eps) -> DetailScreen(item, eps, provider, { view = View.Home; results = null }, { pickEp(it) }) }; View.Player -> stream?.let { PlayerScreen(it) { view = View.Detail } } }
            opts?.let { (ep, options) -> OptModal(ep, options, sel, { res, url -> sel = sel + (res to url) }, { playServer(it) }, { dlServer(it, ep) }, { opts = null }) }
        }
    }
}

@Composable fun BootScreen() { Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) { Column(horizontalAlignment = Alignment.CenterHorizontally) { LogoMark(); Spacer(Modifier.height(24.dp)); CircularProgressIndicator(color = Primary, modifier = Modifier.size(28.dp), strokeWidth = 3.dp); Spacer(Modifier.height(12.dp)); Text("Memulai server…", color = FgDim, fontSize = 13.sp) } } }
@Composable fun ToastBar(text: String, color: Color, onClose: (() -> Unit)? = null) { Surface(color = color.copy(0.9f), shape = SmR, modifier = Modifier.fillMaxWidth().padding(horizontal = 20.dp, vertical = 4.dp)) { Row(Modifier.padding(horizontal = 16.dp, vertical = 10.dp), verticalAlignment = Alignment.CenterVertically) { if (color == Primary) { CircularProgressIndicator(Modifier.size(14.dp), strokeWidth = 2.dp, color = Fg); Spacer(Modifier.width(8.dp)) }; Text(text, color = Fg, fontSize = 13.sp, modifier = Modifier.weight(1f)); onClose?.let { Box(Modifier.size(24.dp).clip(CircleShape).background(Color.White.copy(0.15f)).clickable { it() }, contentAlignment = Alignment.Center) { XIco(12.dp, Fg) } } } } }

@Composable fun RemoteImage(url: String?, mod: Modifier = Modifier, fit: ContentScale = ContentScale.Crop, fallback: @Composable () -> Unit = {}) {
    var bmp by remember(url) { mutableStateOf<ImageBitmap?>(null) }
    LaunchedEffect(url) {
        bmp = withContext(Dispatchers.IO) {
            try {
                if (url.isNullOrBlank()) null else java.net.URL(url).openConnection().let { c ->
                    c.connectTimeout = 8000; c.readTimeout = 8000
                    c.setRequestProperty("User-Agent", "Mozilla/5.0")
                    c.getInputStream().use { ImageIO.read(it)?.toComposeImageBitmap() }
                }
            } catch (_: Exception) { null }
        }
    }
    bmp?.let { Image(it, contentDescription = null, contentScale = fit, modifier = mod) } ?: fallback()
}

@Composable fun PosterBox(itemUrl: String, itemImage: String?, provider: String, mod: Modifier, initials: String, textSize: TextUnit = 22.sp) {
    var cover by remember(itemUrl) { mutableStateOf(itemImage) }
    LaunchedEffect(itemUrl, itemImage) {
        if (cover.isNullOrBlank()) try {
            val r: JsonObject = http.get("$SERVER/api/poster?url=${java.net.URLEncoder.encode(itemUrl, "UTF-8")}&provider=$provider").body()
            val img = r["image"]?.toString()?.trim('"'); if (img != "null" && img?.isNotBlank() == true) cover = img
        } catch (_: Exception) {}
    }
    RemoteImage(cover, mod) { Box(mod, contentAlignment = Alignment.Center) { Text(initials, color = Muted, fontSize = textSize, fontWeight = FontWeight.ExtraBold, fontFamily = HeadFont) } }
}

@Composable fun LogoMark() { Box(Modifier.size(34.dp).clip(SmR).background(Brush.linearGradient(listOf(Primary, Accent))).shd(18.dp, SmR), contentAlignment = Alignment.Center) { Canvas(Modifier.size(16.dp)) { drawPath(Path().apply { moveTo(3f, 1f); lineTo(3f, 15f); lineTo(15f, 8f); close() }, Color.White, style = Fill) } } }
@Composable fun LogoText() { Row { Text("INDO", color = Fg, fontSize = 18.sp, fontWeight = FontWeight.ExtraBold, letterSpacing = 0.5.sp, fontFamily = HeadFont); Text("NIME", fontSize = 18.sp, fontWeight = FontWeight.ExtraBold, letterSpacing = 0.5.sp, fontFamily = HeadFont, style = TextStyle(brush = Brush.horizontalGradient(listOf(Primary2, Accent)))) } }

// ── SVG icons (ported 1:1 from ui/src/App.jsx Ic map, viewBox 24, stroke 2) ──
@Composable fun PlayIco(sz: Dp = 16.dp, tint: Color = Color.White) { Canvas(Modifier.size(sz)) { val u = size.width / 24f; drawPath(Path().apply { moveTo(8f*u, 5.14f*u); lineTo(8f*u, 18.86f*u); lineTo(20.5f*u, 12f*u); close() }, tint) } }
@Composable fun ClockIco(sz: Dp = 18.dp, tint: Color = Primary2) { Canvas(Modifier.size(sz)) { val u = size.width / 24f; drawCircle(tint, radius = 10f*u, style = Stroke(2f*u)); drawLine(tint, Offset(12f*u, 6f*u), Offset(12f*u, 12f*u), 2f*u, cap = StrokeCap.Round); drawLine(tint, Offset(12f*u, 12f*u), Offset(16f*u, 14f*u), 2f*u, cap = StrokeCap.Round) } }
@Composable fun FlameIco(sz: Dp = 18.dp, tint: Color = Primary2) { Canvas(Modifier.size(sz)) { val u = size.width / 24f; drawPath(Path().apply { moveTo(8.5f*u, 14.5f*u); arcTo(Rect(6f*u, 9.5f*u, 11f*u, 14.5f*u), 90f, -90f, false); cubicTo(11f*u, 10.62f*u, 10.5f*u, 10f*u, 10f*u, 9f*u); cubicTo(8.928f*u, 6.857f*u, 9.776f*u, 4.946f*u, 12f*u, 3f*u); cubicTo(12.5f*u, 5.5f*u, 14f*u, 7.9f*u, 16f*u, 9.5f*u); cubicTo(18f*u, 11.1f*u, 19f*u, 13f*u, 19f*u, 15f*u); arcTo(Rect(5f*u, 8f*u, 19f*u, 22f*u), 0f, 180f, false); cubicTo(5f*u, 13.847f*u, 5.433f*u, 12.706f*u, 6f*u, 12f*u); arcTo(Rect(6f*u, 9.5f*u, 11f*u, 14.5f*u), 180f, -90f, false); close() }, tint, style = Stroke(2f*u, cap = StrokeCap.Round, join = StrokeJoin.Round)) } }
@Composable fun SearchIco(sz: Dp = 18.dp, tint: Color = Primary2) { Canvas(Modifier.size(sz)) { val u = size.width / 24f; drawCircle(tint, radius = 7f*u, center = Offset(11f*u, 11f*u), style = Stroke(2f*u)); drawLine(tint, Offset(21f*u, 21f*u), Offset(16.7f*u, 16.7f*u), 2f*u, cap = StrokeCap.Round) } }
@Composable fun BackIco(sz: Dp = 18.dp, tint: Color = Fg) { Canvas(Modifier.size(sz)) { val u = size.width / 24f; drawLine(tint, Offset(5f*u, 12f*u), Offset(19f*u, 12f*u), 2f*u, cap = StrokeCap.Round); drawPath(Path().apply { moveTo(12f*u, 5f*u); lineTo(5f*u, 12f*u); lineTo(12f*u, 19f*u) }, tint, style = Stroke(2f*u, cap = StrokeCap.Round, join = StrokeJoin.Round)) } }
@Composable fun HomeIco(sz: Dp = 18.dp, tint: Color = Fg) { Canvas(Modifier.size(sz)) { val u = size.width / 24f; drawPath(Path().apply { moveTo(3f*u, 10f*u); lineTo(12f*u, 3f*u); lineTo(21f*u, 10f*u); lineTo(21f*u, 20f*u); lineTo(19f*u, 22f*u); lineTo(5f*u, 22f*u); lineTo(3f*u, 20f*u); close() }, tint, style = Stroke(2f*u, cap = StrokeCap.Round, join = StrokeJoin.Round)) } }
@Composable fun XIco(sz: Dp = 16.dp, tint: Color = FgDim) { Canvas(Modifier.size(sz)) { val u = size.width / 24f; drawLine(tint, Offset(6f*u, 6f*u), Offset(18f*u, 18f*u), 2f*u, cap = StrokeCap.Round); drawLine(tint, Offset(18f*u, 6f*u), Offset(6f*u, 18f*u), 2f*u, cap = StrokeCap.Round) } }
@Composable fun ChevIco(sz: Dp = 16.dp, tint: Color = Muted, right: Boolean = false) { Canvas(Modifier.size(sz)) { val u = size.width / 24f; val p = Path().apply { if (right) { moveTo(9f*u, 6f*u); lineTo(15f*u, 12f*u); lineTo(9f*u, 18f*u) } else { moveTo(6f*u, 9f*u); lineTo(12f*u, 15f*u); lineTo(18f*u, 9f*u) } }; drawPath(p, tint, style = Stroke(2f*u, cap = StrokeCap.Round, join = StrokeJoin.Round)) } }

@Composable fun TopBar(provider: String, providers: List<String>, onProv: (String) -> Unit, query: String, onQ: (String) -> Unit, onSearch: () -> Unit, onHome: () -> Unit) {
    Surface(color = Color(0xBF0F0F23), shadowElevation = 4.dp, border = BorderStroke(1.dp, Border), modifier = Modifier.fillMaxWidth()) {
        Row(Modifier.height(64.dp).padding(horizontal = 20.dp).fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
            Row(Modifier.clickable { onHome() }, verticalAlignment = Alignment.CenterVertically) { LogoMark(); Spacer(Modifier.width(10.dp)); LogoText() }
            Spacer(Modifier.width(16.dp))
            Surface(shape = PillR, color = Card, border = BorderStroke(1.dp, Border)) { Row(Modifier.padding(4.dp), horizontalArrangement = Arrangement.spacedBy(4.dp)) { providers.forEach { p -> val on = p == provider; Box(Modifier.clip(PillR).clickable { onProv(p) }.then(if (on) Modifier.background(Brush.linearGradient(listOf(Primary, Color(0xFF9D4EDD)))).shd(12.dp, PillR) else Modifier).height(30.dp).padding(horizontal = 16.dp), contentAlignment = Alignment.Center) { Text(p, color = if (on) Color.White else FgDim, fontSize = 13.sp, fontWeight = FontWeight.Medium) } } } }
            Spacer(Modifier.weight(1f))
            Surface(shape = PillR, color = Card, border = BorderStroke(1.dp, Border), modifier = Modifier.width(360.dp)) { Row(Modifier.padding(start = 16.dp, top = 4.dp, bottom = 4.dp, end = 4.dp), verticalAlignment = Alignment.CenterVertically) { BasicTextField(value = query, onValueChange = onQ, textStyle = TextStyle(color = Fg, fontSize = 14.sp), cursorBrush = SolidColor(Primary), singleLine = true, modifier = Modifier.weight(1f).onPreviewKeyEvent { e: androidx.compose.ui.input.key.KeyEvent -> if (e.type == KeyEventType.KeyUp && e.key == Key.Enter) { onSearch(); true } else false }); Spacer(Modifier.width(4.dp)); Box(Modifier.size(32.dp).clip(CircleShape).background(Card2).clickable { onSearch() }, contentAlignment = Alignment.Center) { Canvas(Modifier.size(18.dp)) { drawCircle(Color.Transparent); drawCircle(FgDim, 5.5f, style = Stroke(1.5f), center = Offset(size.width * 0.46f, size.height * 0.46f)); drawLine(FgDim, Offset(size.width * 0.68f, size.height * 0.68f), Offset(size.width * 0.9f, size.height * 0.9f), 1.5f, cap = StrokeCap.Round) } } } }
        }
    }
}

@OptIn(ExperimentalFoundationApi::class)
@Composable fun HomeScreen(catalog: List<CI>?, latest: List<CI>?, featured: List<CI>, results: List<CI>?, query: String, provider: String, onPick: (CI) -> Unit) {
    var genre by remember { mutableStateOf("Semua") }
    val genres = remember(catalog) { listOf("Semua") + (catalog ?: emptyList()).flatMap { it.genre ?: emptyList() }.distinct() }
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(bottom = 64.dp)) {
        if (results != null) { SectionTitle("Hasil untuk \"$query\"") { SearchIco() }; if (results.isEmpty()) Text("Tidak ada hasil.", color = FgDim, modifier = Modifier.padding(start = 20.dp)); else LazyRow(railPad()) { items(results) { CardItem((if (lowEnd) Modifier else Modifier.animateItem(fadeInSpec = tween(400))), it, provider, onPick) } }; return }
        if (featured.isNotEmpty()) Hero(featured, provider, onPick)
        Row(Modifier.fillMaxWidth().padding(horizontal = 20.dp, vertical = 16.dp), horizontalArrangement = Arrangement.spacedBy(16.dp)) { StatBox(catalog?.size?.toString() ?: "—", "Judul anime", Modifier.weight(1f)); StatBox("4K", "Kualitas stream", Modifier.weight(1f)); StatBox("24/7", "Update episode", Modifier.weight(1f)) }
        SectionTitle("Rilis Terbaru") { ClockIco() }
        if (genres.size > 1) Row(Modifier.horizontalScroll(rememberScrollState()).padding(start = 20.dp, end = 20.dp, bottom = 12.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) { genres.forEach { g -> Chip(g, g == genre) { genre = g } } }
        if (latest == null) SkeletonRow() else LazyRow(railPad()) { items(latest.filter { genre == "Semua" || (it.genre ?: emptyList()).contains(genre) }) { CardItem((if (lowEnd) Modifier else Modifier.animateItem(fadeInSpec = tween(400))), it, provider, onPick) } }
        Spacer(Modifier.height(48.dp)); SectionTitle("Paling Populer") { FlameIco() }; if (catalog == null) SkeletonRow(wide = true) else LazyRow(railPad()) { items(catalog.take(8).mapIndexed { i, c -> i to c }) { (r, c) -> RankItem((if (lowEnd) Modifier else Modifier.animateItem(fadeInSpec = tween(400))), r, c, provider, onPick) } }
    }
}

@Composable fun Hero(items: List<CI>, provider: String, onPick: (CI) -> Unit) {
    var idx by remember { mutableIntStateOf(0) }; val n = items.size.coerceAtMost(6); if (n == 0) return
    LaunchedEffect(n) { if (!lowEnd) while (true) { delay(6000); idx = (idx + 1) % n } }; val it = items[idx]
    Box(Modifier.fillMaxWidth().height(560.dp).background(Bg2)) {
        // ponytail: blur 28dp biar cover low-res gak keliatan pixel (parity App.jsx:349); lowEnd skip (software renderer berat)
        if (lowEnd) RemoteImage(it.image_full ?: it.image, Modifier.fillMaxSize(), fallback = {})
        else RemoteImage(it.image_full ?: it.image, Modifier.fillMaxSize().blur(28.dp), fallback = {})
        // ponytail: 2 lapis gradient full-window mahal di SOFTWARE -> lowEnd solven satu box semi-transparan
        if (lowEnd) Box(Modifier.fillMaxSize().background(Bg.copy(0.66f)))
        else { Box(Modifier.fillMaxSize().background(Brush.horizontalGradient(listOf(Bg.copy(0.92f), Bg.copy(0.6f), Bg.copy(0.25f))))); Box(Modifier.fillMaxSize().background(Brush.verticalGradient(listOf(Bg, Color.Transparent)))) }
        Row(Modifier.fillMaxSize().padding(start = 20.dp, top = 48.dp, end = 20.dp, bottom = 88.dp).widthIn(max = 1080.dp), verticalAlignment = Alignment.Bottom) {
            Column(Modifier.weight(1f).widthIn(max = 620.dp)) {
                Surface(shape = PillR, color = Primary.copy(0.14f), border = BorderStroke(1.dp, Primary2.copy(0.3f))) { Row(Modifier.padding(horizontal = 14.dp, vertical = 6.dp), verticalAlignment = Alignment.CenterVertically) { Box(Modifier.size(8.dp).clip(CircleShape).background(Green).shd(8.dp, CircleShape)); Spacer(Modifier.width(8.dp)); Text(provider, color = Primary2, fontSize = 12.sp, fontWeight = FontWeight.SemiBold, letterSpacing = 1.sp) } }
                Spacer(Modifier.height(16.dp)); Text(it.title, color = Fg, fontSize = 52.sp, fontWeight = FontWeight.ExtraBold, lineHeight = 56.sp, letterSpacing = (-0.5).sp, maxLines = 2, overflow = TextOverflow.Ellipsis, fontFamily = HeadFont)
                it.synopsis?.let { s -> Spacer(Modifier.height(12.dp)); Text(s, color = FgDim, fontSize = 16.sp, lineHeight = 24.sp, maxLines = 3, overflow = TextOverflow.Ellipsis) }
                Spacer(Modifier.height(24.dp)); Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) { PrimaryBtn("Lihat Detail", icon = { PlayIco(20.dp) }) { onPick(it) }; if (it.ep != null) GhostBtn("Episode ${it.ep}", icon = { ClockIco(16.dp) }) { onPick(it) } }
            }
            Spacer(Modifier.width(32.dp))
            RemoteImage(it.image ?: it.image_full, Modifier.width(200.dp).aspectRatio(2f / 3f).clip(RoundedCornerShape(14.dp)).border(1.dp, Color.White.copy(0.14f), RoundedCornerShape(14.dp)), fallback = {})
        }
        Box(Modifier.align(Alignment.CenterStart).padding(start = 16.dp).size(44.dp).clip(CircleShape).background(Bg.copy(0.5f)).border(1.dp, Border, CircleShape).clickable { idx = (idx - 1 + n) % n }, contentAlignment = Alignment.Center) { Text("‹", color = Fg, fontSize = 22.sp) }
        Box(Modifier.align(Alignment.CenterEnd).padding(end = 16.dp).size(44.dp).clip(CircleShape).background(Bg.copy(0.5f)).border(1.dp, Border, CircleShape).clickable { idx = (idx + 1) % n }, contentAlignment = Alignment.Center) { Text("›", color = Fg, fontSize = 22.sp) }
        Row(Modifier.align(Alignment.BottomCenter).padding(bottom = 20.dp), horizontalArrangement = Arrangement.spacedBy(6.dp)) { repeat(n) { i -> Box(Modifier.width(44.dp).height(4.dp).clip(RoundedCornerShape(2.dp)).background(if (i == idx) Brush.horizontalGradient(listOf(Primary2, Accent)) else SolidColor(Color.White.copy(0.22f))).clickable { idx = i }) } }
    }
}

@Composable fun PrimaryBtn(text: String, icon: (@Composable () -> Unit)? = null, onClick: () -> Unit) { Box(Modifier.clip(PillR).background(Brush.linearGradient(listOf(Primary, Color(0xFF9D4EDD)))).shd(24.dp, PillR).clickable(onClick = onClick).height(46.dp).padding(horizontal = 22.dp), contentAlignment = Alignment.Center) { Row(verticalAlignment = Alignment.CenterVertically) { icon?.let { it(); Spacer(Modifier.width(8.dp)) }; Text(text, color = Color.White, fontSize = 14.sp, fontWeight = FontWeight.SemiBold) } } }
@Composable fun GhostBtn(text: String, icon: (@Composable () -> Unit)? = null, onClick: () -> Unit) { Box(Modifier.clip(PillR).background(Color.White.copy(0.06f)).border(1.dp, Border, PillR).clickable(onClick = onClick).height(46.dp).padding(horizontal = 22.dp), contentAlignment = Alignment.Center) { Row(verticalAlignment = Alignment.CenterVertically) { icon?.let { it(); Spacer(Modifier.width(8.dp)) }; Text(text, color = Fg, fontSize = 14.sp, fontWeight = FontWeight.SemiBold) } } }

fun railPad() = Modifier.padding(horizontal = 20.dp, vertical = 4.dp)
// ponytail: shadow blur mahal di SOFTWARE renderer -> lowEnd no-op, border aja yang nahan
fun Modifier.shd(radius: Dp, shape: Shape) = if (lowEnd) this else this.shadow(radius, shape)
@Composable fun SectionTitle(text: String, icon: (@Composable () -> Unit)? = null) { Row(Modifier.fillMaxWidth().padding(start = 20.dp, top = 28.dp, bottom = 16.dp), verticalAlignment = Alignment.CenterVertically) { if (icon != null) { Box(Modifier.size(34.dp).clip(SmR).background(Primary.copy(0.14f)).border(1.dp, Primary2.copy(0.25f), SmR), contentAlignment = Alignment.Center) { icon() }; Spacer(Modifier.width(10.dp)) }; Text(text, color = Fg, fontSize = 22.sp, fontWeight = FontWeight.Bold, letterSpacing = (-0.3).sp, fontFamily = HeadFont); Spacer(Modifier.width(8.dp)); Box(Modifier.weight(1f).height(1.dp).background(Brush.horizontalGradient(listOf(Border, Color.Transparent)))) } }
@Composable fun StatBox(v: String, l: String, mod: Modifier = Modifier) { Column(mod.clip(CardR).background(Brush.linearGradient(listOf(Card, Bg2))).border(1.dp, Border, CardR).padding(18.dp, 22.dp)) { Text(v, fontSize = 26.sp, fontWeight = FontWeight.ExtraBold, fontFamily = HeadFont, style = TextStyle(brush = Brush.horizontalGradient(listOf(Primary2, Accent)))); Spacer(Modifier.height(2.dp)); Text(l, color = Muted, fontSize = 13.sp) } }
@Composable fun CardItem(modifier: Modifier = Modifier, item: CI, provider: String, onPick: (CI) -> Unit) {
    val hov = remember { MutableInteractionSource() }; val hovered by hov.collectIsHoveredAsState()
    val sc = if (lowEnd) 1f else animateFloatAsState(if (hovered) 1.07f else 1f, label = "scale").value
    Column(modifier.width(165.dp).clickable { onPick(item) }.padding(end = 18.dp)) {
        Box(Modifier.fillMaxWidth().aspectRatio(2f / 3f).hoverable(hov).graphicsLayer { scaleX = sc; scaleY = sc; transformOrigin = TransformOrigin.Center }.clip(CardR).background(Card).border(1.dp, Border, CardR)) { PosterBox(item.url, item.image, provider, Modifier.fillMaxSize(), item.title.take(2).uppercase()) }
        Column(Modifier.padding(top = 10.dp, start = 4.dp, end = 4.dp)) { Text(item.title, color = if (hovered) Primary2 else Fg, fontSize = 14.sp, fontWeight = FontWeight.Medium, lineHeight = 19.sp, maxLines = 2, overflow = TextOverflow.Ellipsis); item.ep?.let { Text(it, color = Muted, fontSize = 12.sp, modifier = Modifier.padding(top = 2.dp)) } }
    }
}
@Composable fun RankItem(modifier: Modifier = Modifier, rank: Int, item: CI, provider: String, onPick: (CI) -> Unit) {
    val hov = remember { MutableInteractionSource() }; val hovered by hov.collectIsHoveredAsState()
    val ty = if (lowEnd) 0f else animateFloatAsState(if (hovered) -2f else 0f, label = "lift").value
    Row(modifier.width(340.dp).padding(end = 18.dp).clip(CardR).background(if (hovered) Card2 else Card).border(1.dp, if (hovered) Primary2.copy(0.35f) else Border, CardR).hoverable(hov).graphicsLayer { translationY = ty }.clickable { onPick(item) }.padding(10.dp), verticalAlignment = Alignment.CenterVertically) {
        Text(String.format("%02d", rank + 1), fontSize = 26.sp, fontWeight = FontWeight.ExtraBold, fontFamily = HeadFont, style = TextStyle(brush = Brush.verticalGradient(listOf(Primary2, Accent))), modifier = Modifier.width(40.dp), textAlign = TextAlign.Center)
        PosterBox(item.url, item.image, provider, Modifier.size(64.dp, 88.dp).clip(SmR).background(Card).border(1.dp, Border, SmR), item.title.take(2).uppercase(), 16.sp)
        Spacer(Modifier.width(14.dp)); Column(Modifier.weight(1f)) { Text(item.title, color = Fg, fontSize = 14.sp, fontWeight = FontWeight.Medium, maxLines = 1, overflow = TextOverflow.Ellipsis); val meta = listOfNotNull(item.ep?.let { "$it episode" }, item.genre?.take(2)?.joinToString(" · ")).joinToString(" · "); if (meta.isNotBlank()) Text(meta, color = Muted, fontSize = 12.sp, maxLines = 1, overflow = TextOverflow.Ellipsis, modifier = Modifier.padding(top = 4.dp)) }
        ChevIco(18.dp, if (hovered) Primary2 else Muted, right = true)
    }
}
@Composable fun SkeletonRow(wide: Boolean = false) { LazyRow(railPad()) { items(if (wide) 5 else 8) { Box(Modifier.padding(end = 18.dp).width(if (wide) 340.dp else 165.dp).height(if (wide) 108.dp else 270.dp).clip(CardR).background(Card)) } } }

@Composable fun DetailScreen(info: CI, episodes: List<EP>, provider: String, onBack: () -> Unit, onPickEp: (EP) -> Unit) {
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).widthIn(max = 1200.dp).padding(horizontal = 20.dp, vertical = 28.dp)) {
        GhostBtn("Kembali", icon = { BackIco() }) { onBack() }; Spacer(Modifier.height(24.dp))
        Row(Modifier.fillMaxWidth().clip(RoundedCornerShape(20.dp)).background(Brush.linearGradient(listOf(Card, Bg2))).border(1.dp, Border, RoundedCornerShape(20.dp)).padding(24.dp)) {
            PosterBox(info.url, info.image, provider, Modifier.width(220.dp).aspectRatio(2f / 3f).clip(CardR).background(Card).border(1.dp, Border, CardR), info.title.take(2).uppercase(), 28.sp)
            Spacer(Modifier.width(28.dp)); Column(Modifier.weight(1f)) {
                Surface(shape = PillR, color = Primary.copy(0.14f), border = BorderStroke(1.dp, Primary2.copy(0.25f))) { Row(Modifier.padding(horizontal = 14.dp, vertical = 6.dp), verticalAlignment = Alignment.CenterVertically) { Box(Modifier.size(8.dp).clip(CircleShape).background(Green).shd(8.dp, CircleShape)); Spacer(Modifier.width(8.dp)); Text(provider, color = Primary2, fontSize = 12.sp, fontWeight = FontWeight.SemiBold, letterSpacing = 1.sp) } }
                Spacer(Modifier.height(14.dp)); Text(info.title, color = Fg, fontSize = 36.sp, fontWeight = FontWeight.ExtraBold, lineHeight = 40.sp, letterSpacing = (-0.4).sp, maxLines = 2, overflow = TextOverflow.Ellipsis, fontFamily = HeadFont)
                Spacer(Modifier.height(10.dp)); Text(info.synopsis ?: "—", color = FgDim, fontSize = 14.sp, lineHeight = 20.sp, maxLines = 5, overflow = TextOverflow.Ellipsis)
                Spacer(Modifier.height(16.dp)); Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) { PillChip("${episodes.size} episode"); (info.genre ?: emptyList()).take(2).forEach { g -> PillChip(g) } }
                Spacer(Modifier.height(18.dp)); Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) { PrimaryBtn("Putar Episode 1", icon = { PlayIco(20.dp) }) { if (episodes.isNotEmpty()) onPickEp(episodes[0]) }; GhostBtn("Beranda", icon = { HomeIco() }) { onBack() } }
            }
        }
        Spacer(Modifier.height(24.dp)); Text("Episode", color = Fg, fontSize = 22.sp, fontWeight = FontWeight.Bold, letterSpacing = (-0.3).sp); Spacer(Modifier.height(8.dp))
        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            episodes.forEachIndexed { i, ep ->
                val hov = remember { MutableInteractionSource() }; val hovered by hov.collectIsHoveredAsState()
                val tx = if (lowEnd) 0f else animateFloatAsState(if (hovered) 3f else 0f, label = "shift").value
                Row(Modifier.fillMaxWidth().graphicsLayer { translationX = tx }.clip(SmR).background(if (hovered) Card2 else Card).border(1.dp, if (hovered) Primary2.copy(0.35f) else Border, SmR).hoverable(hov).clickable { onPickEp(ep) }.padding(12.dp, 16.dp), verticalAlignment = Alignment.CenterVertically) {
                    Text(String.format("%02d", i + 1), color = Muted, fontSize = 13.sp, fontWeight = FontWeight.Bold, fontFamily = HeadFont, modifier = Modifier.width(32.dp))
                    Text(ep.title, color = Fg, fontSize = 14.sp, modifier = Modifier.weight(1f), maxLines = 1, overflow = TextOverflow.Ellipsis)
                    PlayIco(16.dp, if (hovered) Primary2 else Muted)
                }
            }
        }
        Spacer(Modifier.height(48.dp))
    }
}
@Composable fun PillChip(text: String) { Surface(shape = PillR, color = Primary.copy(0.12f), border = BorderStroke(1.dp, Primary2.copy(0.25f))) { Text(text, color = Primary2, fontSize = 12.sp, fontWeight = FontWeight.Medium, modifier = Modifier.padding(horizontal = 14.dp, vertical = 5.dp)) } }
@Composable fun Chip(text: String, on: Boolean, onClick: () -> Unit) { Box(Modifier.clip(PillR).background(if (on) Brush.linearGradient(listOf(Primary, Color(0xFF9D4EDD))) else SolidColor(Card)).border(1.dp, if (on) Color.Transparent else Border, PillR).shd(if (on) 16.dp else 0.dp, PillR).clickable(onClick = onClick).height(36.dp).padding(horizontal = 18.dp), contentAlignment = Alignment.Center) { Text(text, color = if (on) Color.White else FgDim, fontSize = 13.sp, fontWeight = FontWeight.Medium) } }

@Composable fun DownIco(sz: Dp = 16.dp, tint: Color = Fg) { Canvas(Modifier.size(sz)) { val u = sz.toPx() / 24f; drawLine(tint, Offset(12f*u, 3f*u), Offset(12f*u, 15f*u), 2f*u, cap = StrokeCap.Round); drawPath(Path().apply { moveTo(7f*u, 11f*u); lineTo(12f*u, 16f*u); lineTo(17f*u, 11f*u) }, tint, style = Stroke(2f*u, cap = StrokeCap.Round, join = StrokeJoin.Round)); drawLine(tint, Offset(4f*u, 21f*u), Offset(20f*u, 21f*u), 2f*u, cap = StrokeCap.Round) } }

@Composable fun ResSelect(options: List<Opt>, cur: Opt, onPick: (Opt) -> Unit, mod: Modifier = Modifier) {
    var open by remember { mutableStateOf(false) }
    Box(mod) {
        Box(Modifier.fillMaxWidth().height(38.dp).clip(SmR).background(Brush.verticalGradient(listOf(Bg2, Bg))).border(1.dp, if (open) Primary2.copy(0.45f) else Border, SmR).clickable { open = true }.padding(horizontal = 12.dp), contentAlignment = Alignment.CenterStart) {
            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) { Text(optName(cur.label), color = Fg, fontSize = 13.sp, fontWeight = FontWeight.SemiBold, maxLines = 1, overflow = TextOverflow.Ellipsis, modifier = Modifier.weight(1f)); Spacer(Modifier.width(8.dp)); ChevIco(14.dp, Primary2) }
        }
        DropdownMenu(expanded = open, onDismissRequest = { open = false }, modifier = Modifier.background(Bg2).border(1.dp, Border, SmR)) {
            options.forEach { o -> DropdownMenuItem(text = { Text(optName(o.label), color = if (o.url == cur.url) Primary2 else FgDim, fontSize = 13.sp, fontWeight = if (o.url == cur.url) FontWeight.Bold else FontWeight.Medium) }, onClick = { onPick(o); open = false }, modifier = Modifier.height(36.dp)) }
        }
    }
}

@Composable fun OptModal(ep: EP, options: List<Opt>, sel: Map<String, String>, onPick: (String, String) -> Unit, onPlay: (Opt) -> Unit, onDownload: (Opt) -> Unit, onClose: () -> Unit) {
    // ponytail: pakai window Dialog terpisah (bukan Box overlay di dalam Column utama) —
    // overlay in-root punya z-order/hit-test bermasalah di Skia desktop (tombol gak bisa diklik).
    // upgrade: kalau butuh multi-aksi per grup tanpa scroll, split jadi multi-step wizard.
    Dialog(onDismissRequest = onClose, properties = DialogProperties(usePlatformDefaultWidth = false)) {
        val groups = remember(options) {
            // parity React (App.jsx): browser/embedded player gak bisa decode MKV — hidden dari daftar; TUI/mpv tetep bisa.
            val m = LinkedHashMap<String, MutableList<Opt>>()
            options.filter { !it.label.contains("mkv", ignoreCase = true) }.forEach { o -> val res = OPT_RES.find(o.label)?.groupValues?.getOrNull(1) ?: "Lainnya"; m.getOrPut(res) { mutableListOf() }.add(o) }
            m.map { it.key to it.value }
        }
        Box(Modifier.width(560.dp).clip(CardR).background(Card).border(1.dp, Border, CardR).shd(30.dp, CardR).padding(20.dp)) {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                    Text(ep.title, color = Fg, fontSize = 16.sp, fontWeight = FontWeight.SemiBold, fontFamily = HeadFont, maxLines = 1, overflow = TextOverflow.Ellipsis, modifier = Modifier.weight(1f))
                    Box(Modifier.size(40.dp).clip(CircleShape).clickable { onClose() }, contentAlignment = Alignment.Center) { XIco(16.dp, FgDim) }
                }
                if (options.isEmpty()) {
                    Text("Tidak ada server kompatibel.", color = FgDim, fontSize = 14.sp, modifier = Modifier.fillMaxWidth(), textAlign = TextAlign.Center)
                } else groups.forEach { (res, list) ->
                    val cur = list.firstOrNull { it.url == sel[res] } ?: list.first()
                    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                        Text(res, color = Primary2, fontSize = 13.sp, fontWeight = FontWeight.Bold, letterSpacing = 0.5.sp, modifier = Modifier.width(52.dp))
                        ResSelect(list, cur, { onPick(res, it.url) }, Modifier.weight(1f))
                        Spacer(Modifier.width(10.dp))
                        Box(Modifier.width(1.dp).height(34.dp).background(Border))
                        Spacer(Modifier.width(10.dp))
                        Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                            PrimaryBtn("Play", icon = { PlayIco(14.dp, Color.White) }) { onPlay(cur) }
                            GhostBtn("Download", icon = { DownIco(14.dp, Fg) }) { onDownload(cur) }
                        }
                    }
                }
            }
        }
    }
}

// ── Embedded player (parity React <video>, via JavaFX MediaPlayer in SwingPanel) ──
// ponytail: JavaFX media decode mp4/h264 via Windows Media Foundation; MKV gak didukung
// browser juga (React filter mkv), jadi MKV difilter & fallback tetep mpv. Upgrade:
// ganti ke libmpv render-API kalau butuh semua format embedded.
@Composable fun EmbeddedVideo(url: String, onState: (String) -> Unit) {
    val state by rememberUpdatedState(onState)
    val playerRef = remember { arrayOfNulls<MediaPlayer>(1) }
    DisposableEffect(url) { onDispose { Platform.runLater { playerRef[0]?.dispose() } } }
    SwingPanel(modifier = Modifier.fillMaxSize(), factory = {
        val fxPanel = JFXPanel()
        Platform.runLater {
            try {
                val media = Media(url)
                if (media.error != null) { state("error"); return@runLater }
                val mp = MediaPlayer(media); playerRef[0] = mp
                mp.isAutoPlay = true
                mp.setOnError { state("error") }
                mp.setOnReady {
                    mp.play()
                    state("ready")
                }
                val view = MediaView(mp)
                view.isPreserveRatio = true
                val scene = Scene(StackPane(view))
                fxPanel.scene = scene
                // React <video> full-width: ikutin ukuran panel via scene (JFXPanel gak punya fx property)
                view.fitWidthProperty().bind(scene.widthProperty())
                view.fitHeightProperty().bind(scene.heightProperty())
            } catch (_: Exception) { state("error") }
        }
        fxPanel
    })
}

@Composable fun PlayerScreen(streamUrl: String, onBack: () -> Unit) {
    var state by remember(streamUrl) { mutableStateOf("loading") }  // loading | ready | error
    Column(Modifier.fillMaxSize().widthIn(max = 1200.dp).padding(20.dp)) {
        GhostBtn("Kembali", icon = { BackIco() }) { onBack() }; Spacer(Modifier.height(8.dp))
        Box(Modifier.fillMaxWidth().weight(1f).clip(CardR).background(Card)) {
            EmbeddedVideo(streamUrl) { state = it }
            if (state != "ready") Box(Modifier.fillMaxSize().background(Card), contentAlignment = Alignment.Center) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    if (state == "loading") { CircularProgressIndicator(Modifier.size(30.dp), strokeWidth = 3.dp, color = Primary); Spacer(Modifier.height(12.dp)); Text("Memuat video…", color = FgDim, fontSize = 13.sp) }
                    else { Text("Gagal memuat video.", color = Accent, fontSize = 14.sp, fontWeight = FontWeight.SemiBold); Spacer(Modifier.height(12.dp)); PrimaryBtn("Buka di MPV", icon = { PlayIco(18.dp) }) { try { val mpv = findMpv(); if (mpv != null) Runtime.getRuntime().exec(arrayOf(mpv, "--force-window=yes", "--title=Indonime Player", streamUrl)) else Desktop.getDesktop().browse(URI(streamUrl)) } catch (_: Exception) {} } }
                }
            }
        }
        Text("Video tidak muncul? Coba resolusi atau server lain.", color = FgDim, fontSize = 12.sp, modifier = Modifier.fillMaxWidth().padding(top = 8.dp), textAlign = TextAlign.Center)
    }
}

fun portOpen(port: Int) = try { ServerSocket(port).close(); false } catch (_: Exception) { true }
fun launchServer() {
  try {
    var d = java.io.File(System.getProperty("user.dir"))
    for (i in 1..5) { if (java.io.File(d, "indonime/__init__.py").exists()) break; d = d.parentFile ?: break }
    // prefer repo .venv (punya semua dep server), fallback ke python PATH
    val py = listOf(java.io.File(d, ".venv/Scripts/python.exe").toString(), java.io.File(d, ".venv/bin/python").toString(), "python", "python3", "py")
      .firstOrNull { cmd -> try { ProcessBuilder(cmd, "--version").start().waitFor() == 0 } catch (_: Exception) { false } } ?: "python"
    serverProc = ProcessBuilder(py, "-m", "indonime.app", "--headless").directory(d).redirectErrorStream(true).start()
  } catch (_: Exception) {}
}
