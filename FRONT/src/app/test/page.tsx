'use client'

export default function TestPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100">
      <div className="bg-white p-8 rounded-lg shadow-lg">
        <h1 className="text-3xl font-bold text-center mb-4 text-primary-600">
          בדיקת פרונטאנד
        </h1>
        <p className="text-gray-700 text-center">
          אם אתה רואה את הדף הזה, הפרונטאנד עובד! ✅
        </p>
        <div className="mt-4 text-center">
          <a
            href="/login"
            className="text-primary-600 hover:text-primary-700 underline"
          >
            לך לדף התחברות
          </a>
        </div>
      </div>
    </div>
  )
}

