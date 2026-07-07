import axios, { type AxiosRequestConfig } from 'axios'
import { ElMessage } from 'element-plus'
import type { ApiResp } from './types'

const http = axios.create({
  baseURL: '',
  timeout: 60000,
})

// Inject auth headers from localStorage per space.
http.interceptors.request.use((config) => {
  const manageKey = localStorage.getItem('cs_manage_key')
  const token = localStorage.getItem('cs_participant_token')
  config.headers = config.headers || {}
  if (manageKey) config.headers['X-Manage-Key'] = manageKey
  if (token) config.headers['X-Participant-Token'] = token
  return config
})

http.interceptors.response.use(
  (resp) => resp,
  (error) => {
    const msg = error?.response?.data?.msg || error.message || '请求失败'
    return Promise.reject(new Error(msg))
  },
)

export async function request<T = any>(config: AxiosRequestConfig, silent = false): Promise<T> {
  try {
    const resp = await http.request<ApiResp<T>>(config)
    const body = resp.data
    if (body.code !== 0) {
      if (!silent) ElMessage.error(body.msg || '操作失败')
      throw new Error(body.msg || '操作失败')
    }
    return body.data
  } catch (e: any) {
    if (!silent) ElMessage.error(e.message || '请求失败')
    throw e
  }
}

export default http
