package com.idlefish.relay.shared.util

import java.time.LocalDateTime
import java.time.ZoneId
import java.time.format.DateTimeFormatter

object TimestampUtil {
    private val formatter = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss")

    fun now(): String = LocalDateTime.now(ZoneId.of("Asia/Shanghai")).format(formatter)

    fun format(epochMillis: Long): String =
        LocalDateTime.ofInstant(java.time.Instant.ofEpochMilli(epochMillis), ZoneId.of("Asia/Shanghai"))
            .format(formatter)
}
