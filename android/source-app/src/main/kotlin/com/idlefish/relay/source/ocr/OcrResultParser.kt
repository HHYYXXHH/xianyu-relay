package com.idlefish.relay.source.ocr

object OcrResultParser {

    data class ParsedOcr(
        val text: String,
        val summary: String,
        val orderId: String = "",
        val refundId: String = "",
        val amount: String = "",
        val tradeTime: String = "",
        val status: String = "",
    )

    private val STATUS_MAP = mapOf(
        "已付款" to "paid", "已支付" to "paid", "paid" to "paid", "payment" to "paid",
        "已发货" to "shipped", "shipped" to "shipped",
        "已完成" to "completed", "completed" to "completed", "done" to "completed",
        "已关闭" to "closed", "closed" to "closed",
        "待付款" to "pending_payment", "pending" to "pending_payment",
        "退款中" to "refunding", "refunding" to "refunding",
        "已退款" to "refunded", "退款成功" to "refunded", "refunded" to "refunded",
    )

    fun parse(text: String): ParsedOcr {
        // 清理中文间空格
        var cleaned = text.replace(Regex("(?<=[一-鿿])\\s+(?=[一-鿿])"), "")
        cleaned = cleaned.replace(Regex("(?<=[一-鿿])\\s+(?=[，。：；！？、])"), "")
        cleaned = cleaned.replace(Regex("(?<=[，。：；！？、])\\s+(?=[一-鿿])"), "")

        // 提取订单号
        val orderId = Regex(
            "(?:订单(?:号|编号)?|order\\s*id)[：:\\s]*([A-Za-z0-9_\\-]+)",
            RegexOption.IGNORE_CASE
        ).find(cleaned)?.groupValues?.getOrNull(1) ?: ""

        // 提取退款号
        val refundId = Regex(
            "(?:退款(?:号|编号)?)[：:\\s]*([A-Za-z0-9_\\-]+)",
            RegexOption.IGNORE_CASE
        ).find(cleaned)?.groupValues?.getOrNull(1) ?: ""

        // 提取金额: ¥xxx / RMBxxx / xxx元
        val amount = Regex("[¥￥](\\d+[.]?\\d*)").find(cleaned)?.groupValues?.getOrNull(1)
            ?: Regex("RMB\\s*(\\d+[.]?\\d*)", RegexOption.IGNORE_CASE).find(cleaned)?.groupValues?.getOrNull(1)
            ?: Regex("(\\d+[.]?\\d{0,2})\\s*元").find(cleaned)?.groupValues?.getOrNull(1)
            ?: ""

        // 提取时间
        val tradeTime = Regex(
            "\\d{4}[-/年]\\d{1,2}[-/月]\\d{1,2}(?:日)?(?:\\s*\\d{1,2}:\\d{2})?"
        ).find(cleaned)?.value ?: ""

        // 提取状态
        var status = ""
        var statusKeyword = ""
        for ((keyword, code) in STATUS_MAP) {
            if (cleaned.contains(keyword)) {
                status = code
                statusKeyword = keyword
                break
            }
        }

        // 构建摘要: "已付款，订单号: xxx，金额: xxx元"
        val summaryParts = mutableListOf<String>()
        if (statusKeyword.isNotBlank()) summaryParts.add(statusKeyword)
        if (orderId.isNotBlank()) summaryParts.add("订单号: $orderId")
        if (amount.isNotBlank()) summaryParts.add("金额: ${amount}元")
        val summary = summaryParts.joinToString("，")

        return ParsedOcr(
            text = cleaned,
            summary = summary.ifBlank { cleaned.take(80) },
            orderId = orderId,
            refundId = refundId,
            amount = amount,
            tradeTime = tradeTime,
            status = status,
        )
    }
}
