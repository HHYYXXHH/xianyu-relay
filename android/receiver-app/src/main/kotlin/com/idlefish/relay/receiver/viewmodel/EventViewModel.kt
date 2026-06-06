package com.idlefish.relay.receiver.viewmodel

import androidx.lifecycle.ViewModel
import com.idlefish.relay.receiver.data.EventRepository
import com.idlefish.relay.receiver.data.EventUiModel
import kotlinx.coroutines.flow.StateFlow

class EventViewModel : ViewModel() {

    private val repository = EventRepository()

    val events: StateFlow<List<EventUiModel>> = repository.eventsFlow

    fun addEvent(event: com.idlefish.relay.shared.model.EventRecord) {
        repository.addEvent(event)
    }

    fun markHandled(eventId: String) {
        repository.markHandled(eventId)
    }

    fun getEvent(eventId: String): EventUiModel? {
        return repository.getEvent(eventId)
    }

    fun clear() {
        repository.clear()
    }
}
