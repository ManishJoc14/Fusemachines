"use client"

import { useEffect, useState } from "react"
import Image from "next/image"
import { useRouter } from "next/navigation"
import { GoogleLogin } from "@react-oauth/google"

import assistantLogo from "@/app/icon1.png"
import { Loader } from "@/components/ui/loader"
import { loginWithGoogle } from "@/features/auth/api"
import { useAuth } from "@/features/auth/auth-provider"

export default function LoginPage() {
  const router = useRouter()
  const { status, setAuthenticatedUser } = useAuth()
  const [error, setError] = useState<string | null>(null)
  const [isSigningIn, setIsSigningIn] = useState(false)

  useEffect(() => {
    if (status === "authenticated") router.replace("/chat")
  }, [router, status])

  async function handleGoogleCredential(credential?: string) {
    if (!credential) {
      setError("Google did not return a sign-in credential.")
      return
    }

    setError(null)
    setIsSigningIn(true)
    try {
      const user = await loginWithGoogle(credential)
      setAuthenticatedUser(user)
      router.replace("/chat")
    } catch (loginError) {
      setError(
        loginError instanceof Error ? loginError.message : "Sign in failed"
      )
      setIsSigningIn(false)
    }
  }

  if (status === "loading" || status === "authenticated" || isSigningIn) {
    return <FullPageLoader message="Signing you in…" />
  }

  return (
    <main className="flex min-h-svh items-center justify-center px-5 py-10">
      <section className="w-full max-w-sm rounded-2xl border bg-card p-8 shadow-sm">
        <Image
          alt="AI Assistant"
          className="mx-auto size-11 rounded-full"
          height={44}
          priority
          src={assistantLogo}
          width={44}
        />
        <div className="mt-5 text-center">
          <h1 className="text-2xl font-semibold tracking-tight">
            Welcome back
          </h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Sign in to access your chats and documents.
          </p>
        </div>

        <div className="mt-7 flex justify-center">
          <GoogleLogin
            onError={() => setError("Google sign in could not be started.")}
            onSuccess={(response) =>
              handleGoogleCredential(response.credential)
            }
            shape="pill"
            size="large"
            text="continue_with"
            theme="outline"
            width="300"
          />
        </div>

        {error ? (
          <p
            aria-live="polite"
            className="mt-4 text-center text-sm text-destructive"
          >
            {error}
          </p>
        ) : null}

        <p className="mt-6 text-center text-xs leading-5 text-muted-foreground">
          By continuing, you agree to use the assistant responsibly.
        </p>
      </section>
    </main>
  )
}

function FullPageLoader({ message }: { message: string }) {
  return (
    <main className="flex min-h-svh items-center justify-center">
      <div className="flex flex-col items-center gap-3 text-center">
        <Loader aria-label={message} variant="circular" />
        <p className="text-sm text-muted-foreground">{message}</p>
        <p className="text-xs text-muted-foreground/80">
          The server may take up to a minute to wake after inactivity.
        </p>
      </div>
    </main>
  )
}
