import { useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'

export default function AuthCallback() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()

  useEffect(() => {
    const token = searchParams.get('token')
    if (token) {
      localStorage.setItem('token', token)
      navigate('/dashboard')
    } else {
      navigate('/auth')
    }
  }, [navigate, searchParams])

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#FAFAFA] p-4">
      <div className="text-center">
        <h2 className="text-xl font-semibold text-[#171717]">Authenticating...</h2>
        <p className="text-sm text-[#737373]">Please wait while we log you in.</p>
      </div>
    </div>
  )
}
