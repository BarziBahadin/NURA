import React, { useEffect, useRef, useState } from 'react'
import { Room, RoomEvent, createLocalAudioTrack } from 'livekit-client'
import { Microphone, MicrophoneSlash, PhoneDisconnect } from '@phosphor-icons/react'

export default function LiveVoiceCall({ call, onEnd }) {
  const [status, setStatus] = useState('idle')
  const [muted, setMuted] = useState(false)
  const [participants, setParticipants] = useState(0)
  const roomRef = useRef(null)
  const trackRef = useRef(null)

  function cleanupConnection({ disconnect = true } = {}) {
    const room = roomRef.current
    trackRef.current?.stop()
    trackRef.current = null
    roomRef.current = null
    if (disconnect) room?.disconnect()
    setParticipants(0)
    setMuted(false)
  }

  useEffect(() => {
    return () => {
      cleanupConnection()
    }
  }, [])

  async function join() {
    if (!call?.server_url || !call?.livekit_token || roomRef.current) return
    setStatus('connecting')
    try {
      const room = new Room({ adaptiveStream: true, dynacast: true })
      roomRef.current = room
      room.on(RoomEvent.ParticipantConnected, () => setParticipants(room.remoteParticipants.size))
      room.on(RoomEvent.ParticipantDisconnected, () => setParticipants(room.remoteParticipants.size))
      room.on(RoomEvent.Disconnected, () => {
        setStatus('ended')
        cleanupConnection({ disconnect: false })
      })
      await room.connect(call.server_url, call.livekit_token)
      const track = await createLocalAudioTrack({ echoCancellation: true, noiseSuppression: true })
      trackRef.current = track
      await room.localParticipant.publishTrack(track)
      setParticipants(room.remoteParticipants.size)
      setStatus('connected')
    } catch (e) {
      console.error(e)
      cleanupConnection()
      setStatus('error')
    }
  }

  function toggleMute() {
    if (!trackRef.current) return
    if (muted) trackRef.current.unmute()
    else trackRef.current.mute()
    setMuted(!muted)
  }

  function leave() {
    cleanupConnection()
    setStatus('ended')
    onEnd?.()
  }

  return (
    <div className="mt-3 rounded-xl border border-orange-100 bg-orange-50 p-3">
      <div className="flex items-center justify-between gap-3">
        <div>
          <div className="text-sm font-bold text-orange-900">NURA Voice</div>
          <div className="text-xs text-orange-700">
            {status === 'idle' && 'Ready to join the customer'}
            {status === 'connecting' && 'Connecting...'}
            {status === 'connected' && `${participants} other participant${participants === 1 ? '' : 's'}`}
            {status === 'ended' && 'Call ended'}
            {status === 'error' && 'Could not connect'}
          </div>
        </div>
        {status !== 'connected' ? (
          <button
            onClick={join}
            className="px-3 py-2 rounded-lg bg-orange-600 text-white text-sm font-semibold hover:bg-orange-700"
          >
            Join
          </button>
        ) : (
          <div className="flex gap-2">
            <button
              onClick={toggleMute}
              className="w-9 h-9 rounded-lg bg-white border border-orange-200 text-orange-700 flex items-center justify-center"
              title={muted ? 'Unmute' : 'Mute'}
            >
              {muted ? <MicrophoneSlash size={18} /> : <Microphone size={18} />}
            </button>
            <button
              onClick={leave}
              className="w-9 h-9 rounded-lg bg-red-600 text-white flex items-center justify-center"
              title="Leave call"
            >
              <PhoneDisconnect size={18} />
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
