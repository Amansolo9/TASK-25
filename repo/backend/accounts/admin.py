from django.contrib import admin

from accounts.models import (
    AccountDeletionRequest,
    CaptchaChallenge,
    ComparisonItem,
    DataExportRequest,
    FavoriteItem,
    LocalSubscriptionAlert,
    PasswordHistory,
    TravelerProfile,
    User,
    UserPreference,
    UserRole,
    VerificationDocument,
    VerificationRequest,
    VerificationReview,
)

admin.site.register(User)
admin.site.register(UserRole)
admin.site.register(PasswordHistory)
admin.site.register(CaptchaChallenge)
admin.site.register(VerificationRequest)
admin.site.register(VerificationDocument)
admin.site.register(VerificationReview)
admin.site.register(UserPreference)
admin.site.register(TravelerProfile)
admin.site.register(FavoriteItem)
admin.site.register(ComparisonItem)
admin.site.register(LocalSubscriptionAlert)
admin.site.register(DataExportRequest)
admin.site.register(AccountDeletionRequest)
