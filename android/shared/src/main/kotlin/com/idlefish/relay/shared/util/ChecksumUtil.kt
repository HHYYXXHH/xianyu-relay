package com.idlefish.relay.shared.util

import java.security.MessageDigest

object ChecksumUtil {
    fun md5Short(text: String): String {
        val digest = MessageDigest.getInstance("MD5")
        val hash = digest.digest(text.toByteArray(Charsets.UTF_8))
        return hash.joinToString("") { "%02x".format(it) }.take(8)
    }
}
