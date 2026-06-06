package com.idlefish.relay.source.service

import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.AccessibilityServiceInfo
import android.content.Intent
import android.graphics.Bitmap
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.util.DisplayMetrics
import android.view.accessibility.AccessibilityEvent
import com.google.android.gms.tasks.Tasks
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.text.TextRecognition
import com.google.mlkit.vision.text.chinese.ChineseTextRecognizerOptions
import com.idlefish.relay.source.IdlefishRelayApp
import com.idlefish.relay.source.handler.MessageDispatcher
import com.idlefish.relay.source.parser.NotificationParser
import com.idlefish.relay.shared.util.TimestampUtil
import kotlinx.coroutines.*
import kotlin.coroutines.resume

class XianyuAccessibilityService : AccessibilityService() {

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private val dispatcher = MessageDispatcher()
    private val handler = Handler(Looper.getMainLooper())
    private val sentKeys = LinkedHashSet<String>(500)
    private var processing = false
    private var lastCaptureTime = 0L
    private var screenWidth = 0

    private val recognizer by lazy {
        TextRecognition.getClient(ChineseTextRecognizerOptions.Builder().build())
    }

    override fun onServiceConnected() {
        super.onServiceConnected()
        screenWidth = resources.displayMetrics.widthPixels
        serviceInfo = AccessibilityServiceInfo().apply {
            eventTypes = AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED or AccessibilityEvent.TYPE_WINDOW_CONTENT_CHANGED
            feedbackType = AccessibilityServiceInfo.FEEDBACK_GENERIC
            flags = AccessibilityServiceInfo.FLAG_INCLUDE_NOT_IMPORTANT_VIEWS or
                    AccessibilityServiceInfo.FLAG_REPORT_VIEW_IDS or
                    AccessibilityServiceInfo.DEFAULT
            notificationTimeout = 2000
        }
        NotificationMonitorService.addLog("无障碍OCR ✓")
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        event ?: return
        if (event.packageName?.toString() != "com.taobao.idlefish") return
        if (processing) return
        if (System.currentTimeMillis() - lastCaptureTime < 8000) return

        processing = true
        lastCaptureTime = System.currentTimeMillis()

        handler.postDelayed({
            scope.launch {
                try {
                    captureAndProcess()
                } catch (e: Exception) {
                    NotificationMonitorService.addLog("OCR异常:${e.message?.take(15)}")
                } finally { processing = false }
            }
        }, 2500)
    }

    private suspend fun captureAndProcess() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
            NotificationMonitorService.addLog("需Android14+")
            return
        }

        val text = suspendCancellableCoroutine<String> { cont ->
            try {
                takeScreenshot(DisplayMetrics.DENSITY_DEVICE_STABLE,
                    java.util.concurrent.Executors.newSingleThreadExecutor(),
                    object : TakeScreenshotCallback {
                        override fun onSuccess(s: ScreenshotResult) {
                            scope.launch {
                                try {
                                    val bmp = Bitmap.wrapHardwareBuffer(s.hardwareBuffer, s.colorSpace)
                                    s.hardwareBuffer.close()
                                    if (bmp == null) { cont.resume("") {}; return@launch }
                                    val img = InputImage.fromBitmap(bmp, 0)
                                    val txt = Tasks.await(recognizer.process(img))
                                    val sb = StringBuilder()
                                    for (blk in txt.textBlocks) for (ln in blk.lines) {
                                        val t = ln.text.trim(); if (t.isNotEmpty()) sb.appendLine(t)
                                    }
                                    cont.resume(sb.toString().trim()) {}
                                } catch (_: Exception) {
                                    try { s.hardwareBuffer.close() } catch (_: Exception) {}
                                    cont.resume("") {}
                                }
                            }
                        }
                        override fun onFailure(code: Int) { cont.resume("") {} }
                    })
            } catch (_: Exception) { cont.resume("") {} }
        }

        if (text.isBlank()) { NotificationMonitorService.addLog("OCR无内容"); return }

        val lines = text.split("\n").map { it.trim() }.filter { line ->
            line.length in 5..600 &&
            line !in NOISE &&
            !line.matches(Regex("^[\\d.,:;，。：；()（）\\s·\\-＆/\$¥€£￥]+$")) &&
            !line.startsWith("http")
        }
        if (lines.isEmpty()) { NotificationMonitorService.addLog("过滤后为空"); return }

        var n = 0
        for (msg in merge(lines)) {
            val k = msg.take(40)
            if (k !in sentKeys) {
                sentKeys.add(k)
                if (sentKeys.size > 500) { val it = sentKeys.iterator(); it.next(); it.remove() }
                dispatcher.dispatch(NotificationParser.ParsedMessage(
                    messageKey = "ocr_${System.currentTimeMillis()}_${k.hashCode().and(0xFFFF)}",
                    threadKey = "xianyu", timestamp = TimestampUtil.now(),
                    source = "ocr", title = "闲鱼", text = msg,
                    imageUris = emptyList(), rawKey = k,
                ))
                n++
            }
        }
        if (n > 0) NotificationMonitorService.addLog("OCR提取 $n 条")
    }

    private fun merge(lines: List<String>): List<String> {
        val out = mutableListOf<String>(); var b = ""
        for (l in lines) {
            if (b.length + l.length < 500) b = if (b.isEmpty()) l else "$b\n$l"
            else { out.add(b); b = l }
        }
        if (b.isNotEmpty()) out.add(b)
        return out
    }

    override fun onInterrupt() {}
    override fun onDestroy() { NotificationMonitorService.addLog("无障碍断连"); super.onDestroy() }

    companion object {
        private val NOISE = setOf(
            "发送","输入","图片","拍照","语音","表情","更多","红包","转账",
            "评价","分享","举报","投诉","复制","删除","撤回","引用","提醒",
            "转发","搜索","扫一扫","消息","首页","我的","发布","关注",
            "推荐","热门","购物车","客服","登录","注册","联系买家","查看钱款",
            "确认","取消","确定","返回","关闭","知道了","好的","去发布",
            "支付宝","微信","拼多多","淘宝","京东","百度网盘",
            "设置","版本","关于","更新","退出","通知","提示","账单","筛选",
            "鱼力值","帮我助力","今日曝光","赚钱","买闲置","发闲置","同城",
            "帮助与客服","历史浏览","我的收藏","我的关注","红包卡券",
            "闲鱼","消息","卖闲置","鱼小铺","闲小蜜","卖家小助手",
            "闲鱼精选","通知消息","互动消息","平台","快乐","头像",
            "更多选择","语音按钮","表情按钮","商品图片","商品信息",
            "二手车","租房","二手房","免打扰开启","清除未读","查看评价",
            "奶酪圈圈","深深的杂货铺","商品详情","已读","昨天","今天",
            "价格","运费","库存","全新","几乎全新","订单详情","退款",
            "第","共","按钮","去逛逛","去看看","要买","想买","浏览","想要",
            "以下广告","猜你喜欢","为你推荐","继续拖动","查看全部",
            "回复","点击","长按","滑动","上滑","下滑","左滑","右滑",
        )

        fun isAccessibilityEnabled(ctx: android.content.Context): Boolean {
            val s = android.provider.Settings.Secure.getString(ctx.contentResolver, android.provider.Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES) ?: return false
            return s.contains(ctx.packageName ?: "")
        }
        fun openAccessibilitySettings(ctx: android.content.Context) {
            ctx.startActivity(android.content.Intent(android.provider.Settings.ACTION_ACCESSIBILITY_SETTINGS))
        }
    }
}
