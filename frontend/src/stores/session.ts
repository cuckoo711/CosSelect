import { defineStore } from 'pinia'

type Role = 'leader' | 'participant' | null

interface SessionState {
  spaceId: string | null
  role: Role
  manageKey: string | null
  inviteCode: string | null
  participantToken: string | null
  nickname: string | null
}

export const useSessionStore = defineStore('session', {
  state: (): SessionState => ({
    spaceId: localStorage.getItem('cs_space_id') || null,
    role: (localStorage.getItem('cs_role') as Role) || null,
    manageKey: localStorage.getItem('cs_manage_key'),
    inviteCode: localStorage.getItem('cs_invite_code'),
    participantToken: localStorage.getItem('cs_participant_token'),
    nickname: localStorage.getItem('cs_nickname'),
  }),

  getters: {
    isLeader: (s) => s.role === 'leader',
    isParticipant: (s) => s.role === 'participant',
    displayName: (s) => (s.role === 'leader' ? '团长' : s.nickname || ''),
    authed: (s) => !!s.spaceId && !!s.role,
  },

  actions: {
    setLeader(spaceId: string, manageKey: string, inviteCode?: string) {
      this.spaceId = spaceId
      this.role = 'leader'
      this.manageKey = manageKey
      if (inviteCode) this.inviteCode = inviteCode
      this.participantToken = null
      this.nickname = null
      this.persist()
    },

    setParticipant(spaceId: string, token: string, nickname: string) {
      this.spaceId = spaceId
      this.role = 'participant'
      this.participantToken = token
      this.nickname = nickname
      this.manageKey = null
      this.persist()
    },

    setInviteCode(code: string) {
      this.inviteCode = code
      localStorage.setItem('cs_invite_code', code)
    },

    persist() {
      const set = (k: string, v: string | null) =>
        v ? localStorage.setItem(k, v) : localStorage.removeItem(k)
      set('cs_space_id', this.spaceId ? String(this.spaceId) : null)
      set('cs_role', this.role)
      set('cs_manage_key', this.manageKey)
      set('cs_invite_code', this.inviteCode)
      set('cs_participant_token', this.participantToken)
      set('cs_nickname', this.nickname)
    },

    logout() {
      this.spaceId = null
      this.role = null
      this.manageKey = null
      this.inviteCode = null
      this.participantToken = null
      this.nickname = null
      ;['cs_space_id', 'cs_role', 'cs_manage_key', 'cs_invite_code', 'cs_participant_token', 'cs_nickname'].forEach(
        (k) => localStorage.removeItem(k),
      )
    },
  },
})
