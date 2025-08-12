import uuid
from django.db import models

# Choices with (code, English, Amharic)
AGE_RANGES = [
    ('U15', 'Under 15', 'ከ15 ዓመት በታች'),
    ('A15_19', '15–19', '15–19'),
    ('A20_24', '20–24', '20–24'),
    ('A25_34', '25–34', '25–34'),
    ('A35_44', '35–44', '35–44'),
    ('O45', '45+', 'ከ45 ዓመት በላይ'),
]

GENDERS = [
    ('F', 'Female', 'ሴት'),
    ('M', 'Male', 'ወንድ'),
]

INTEREST_AREAS = [
    ('CONTRACEPTION', 'Contraception', 'የወሊድ መቆጣጠሪያ'),
    ('MENSTRUATION', 'Menstruation', 'የወር አበባ'),
    ('PREGNANCY', 'Pregnancy', 'እርግዝና'),
    ('STI_HIV', 'STIs & HIV', 'አባላዘር በሽታዎች (STIs) እና ኤችአይቪ'),
    ('CONSENT_REL', 'Consent & Healthy Relationships', 'ስምምነት እና ጤናማ ግንኙነት'),
    ('EMERGENCY', 'Emergency Support', 'የድንገተኛ ጊዜ ድጋፍ'),
    ('EXPLORING', 'Just exploring', 'ዝም ብዬ ማሰስ'),
]

REGIONS = [
    ('ADDIS_ABABA', 'Addis Ababa City Administration', 'አዲስ አበባ ከተማ አስተዳደር'),
    ('AFAR', 'Afar Region', 'አፋር ክልል'),
    ('AMHARA', 'Amhara Region', 'አማራ ክልል'),
    ('BENISHANGUL', 'Benishangul-Gumuz Region', 'ቤኒሻንጉል ጉሙዝ ክልል'),
    ('CENTRAL_ETH', 'Central Ethiopia Region', 'የማዕከላዊ ኢትዮጵያ ክልል'),
    ('DIRE_DAWA', 'Dire Dawa City Administration', 'ድሬዳዋ ከተማ አስተዳደር'),
    ('GAMBELA', 'Gambela Region', 'ጋምቤላ ክልል'),
    ('HARARI', 'Harari Region', 'ሐረሪ ክልል'),
    ('OROMIA', 'Oromia Region', 'ኦሮሚያ ክልል'),
    ('SIDAMA', 'Sidama Region', 'ሲዳማ ክልል'),
    ('SOUTH_ETH', 'South Ethiopia Region', 'የደቡብ ኢትዮጵያ ክልል'),
    ('SOMALI', 'Somali Region', 'ሶማሌ ክልል'),
    ('SOUTHWEST', 'South West Ethiopia Peoples\' Region', 'የደቡብ ምዕራብ ኢትዮጵያ ሕዝቦች ክልል'),
    ('TIGRAY', 'Tigray Region', 'ትግራይ ክልል'),
]

RATING_CHOICES = [
    ('VERY_HELPFUL', '👍🏾 Very helpful', '👍🏾 በጣም ጠቃሚ'),
    ('SOMEWHAT_HELPFUL', '🙂Somewhat helpful', '🙂 ትንሽ ጠቃሚ'),
    ('NOT_VERY', '😐Not very helpful', '😐 ያን ያህል ጠቃሚ አይደለም'),
    ('NOT_HELPFUL', '👎🏾 Not helpful at all', '👎🏾 በፍጹም ጠቃሚ አይደለም'),
]

INTENT_CHOICES = [
    ('ASK_INFO', 'Ask for Information', 'መረጃ መጠየቅ'),
    ('ASK_ACTION', 'Ask for Action/Help', 'እርዳታ/እርምጃ መጠየቅ'),
    ('REPORT_INCIDENT', 'Report an Incident', 'ክስተት ሪፖርት ማድረግ'),
    ('EXPRESS_EMOTION', 'Express Emotion', 'ስሜት መግለጽ'),
    ('ASK_CONFIDENTIALITY', 'Ask for Confidentiality', 'ሚስጥራዊነት መጠየቅ'),
    ('SEEK_VALIDATION', 'Seek Validation', 'ማረጋገጫ መሻት'),
    ('REFUSE_HELP', 'Refuse Help', 'እርዳታ ማጣት'),
    ('OTHER', 'Other', 'ሌላ'),
]

EMOTION_CHOICES = [
    ('FEAR', 'Fear', 'ፍርሃት'),
    ('SHAME', 'Shame', 'ውርደት'),
    ('CONFUSION', 'Confusion', 'ግዞት'),
    ('SADNESS', 'Sadness', 'ሀዘን'),
    ('ANGER', 'Anger', 'ቁጣ'),
    ('HELPLESSNESS', 'Helplessness', 'ስቃይ'),
    ('NEUTRAL', 'Neutral', 'ገለልተኛ'),
]

EMOTION_RATING_CHOICES = [
    (0, 'Not Present', 'የለም'),
    (1, 'Mild', 'መካከለኛ'),
    (2, 'Strong', 'ጠንካራ'),
]

RISK_LEVEL_CHOICES = [
    ('ABUSE', 'Physical/Sexual Abuse', 'አካላዊ/ጾታዊ ሁከት'),
    ('DOMESTIC_VIOLENCE', 'Domestic Violence', 'የቤት ውስጥ ሁከት'),
    ('SELF_HARM', 'Self-Harm/Suicide Risk', 'እራስን ማጥፋት/ራስን ማጥፋት አደጋ'),
    ('ILLEGAL_ABORTION', 'Unsafe/Illegal Abortion', 'ደህንነቱ ያልተጠበቀ/ሕገወጥ ፅንስ ማስወረድ'),
    ('SEXUAL_VIOLENCE', 'Sexual Violence/Rape', 'ጾታዊ ሁከት/መደፈር'),
    ('UNSAFE_PRACTICES', 'Unsafe Sexual Practices', 'ደህንነቱ ያልተጠበቀ ጾታዊ ባህሪ'),
    ('CRISIS', 'Mental Health Crisis', 'የአእምሮ ጤና ቀውስ'),
    ('NEUTRAL', 'No Risk Detected', 'አደጋ አልተገኘም'),
]

MYTH_DETECTION_CHOICES = [
    # Cultural/Traditional Myths
    ('CULTURAL_HYMEN', 'Hymen/Virginity Myths', 'የባክነት/ቅድስና አፈታሪኮች'),
    ('CULTURAL_MENSTRUATION', 'Menstrual Cultural Myths', 'የወር አበባ ባህላዊ አፈታሪኮች'),
    ('CULTURAL_FERTILITY', 'Fertility/Infertility Myths', 'የመውለድ አቅም አፈታሪኮች'),
    ('CULTURAL_PREGNANCY', 'Pregnancy Cultural Beliefs', 'የእርግዝና ባህላዊ እምነቶች'),
    ('CULTURAL_CONTRACEPTION', 'Contraception Cultural Myths', 'የወሊድ መቆጣጠሪያ ባህላዊ አፈታሪኮች'),
    
    # Medical Misconceptions
    ('MEDICAL_CONTRACEPTION', 'Contraception Medical Misconceptions', 'የወሊድ መቆጣጠሪያ ሕክምናዊ ስህተቶች'),
    ('MEDICAL_STI', 'STI/HIV Medical Misconceptions', 'የSTI/HIV ሕክምናዊ ስህተቶች'),
    ('MEDICAL_PREGNANCY', 'Pregnancy Medical Misconceptions', 'የእርግዝና ሕክምናዊ ስህተቶች'),
    ('MEDICAL_ANATOMY', 'Anatomy/Biology Misconceptions', 'የሰውነት አቀማመጥ ሕክምናዊ ስህተቶች'),
    ('MEDICAL_PUBERTY', 'Puberty Medical Misconceptions', 'የእድሜ ብስለት ሕክምናዊ ስህተቶች'),
    ('MEDICAL_MENSTRUATION', 'Menstruation Medical Misconceptions', 'የወር አበባ ሕክምናዊ ስህተቶች'),
    
    # No myth detected
    ('NO_MYTH', 'No Myth Detected', 'አፈታሪክ አልተገኘም'),
]

class UserSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    telegram_user_id = models.BigIntegerField(db_index=True)
    language = models.CharField(max_length=2, choices=[('en', 'English'), ('am', 'Amharic')])
    age_range = models.CharField(max_length=16, choices=[(x[0], x[1]) for x in AGE_RANGES])
    gender = models.CharField(max_length=8, choices=[(x[0], x[1]) for x in GENDERS])
    interest_area = models.CharField(max_length=32, choices=[(x[0], x[1]) for x in INTEREST_AREAS])
    region = models.CharField(max_length=32, choices=[(x[0], x[1]) for x in REGIONS], null=True, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, help_text="GPS latitude coordinate")
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, help_text="GPS longitude coordinate")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.telegram_user_id} - {self.language} - {self.age_range}"
    
class ChatMessage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(UserSession, on_delete=models.CASCADE, related_name='messages')
    sender = models.CharField(max_length=8, choices=[('user', 'User'), ('bot', 'Bot')])
    message = models.TextField()
    language = models.CharField(max_length=2, choices=[('en', 'English'), ('am', 'Amharic')])
    timestamp = models.DateTimeField(auto_now_add=True)
    llm_context_json = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"{self.sender} - {self.timestamp} - {self.message[:30]}"

class Feedback(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    chat_message = models.ForeignKey(ChatMessage, on_delete=models.CASCADE, related_name='feedbacks')
    rating = models.CharField(
        max_length=32,
        choices=[(x[0], x[1]) for x in RATING_CHOICES]
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.rating} for {self.chat_message_id}"

class Classification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(UserSession, on_delete=models.CASCADE, related_name='classifications')
    intent = models.CharField(
        max_length=32,
        choices=[(x[0], x[1]) for x in INTENT_CHOICES]
    )
    messages_analyzed = models.PositiveIntegerField(default=10, help_text="Number of messages analyzed for this classification")
    confidence_score = models.FloatField(null=True, blank=True, help_text="AI confidence in classification (0-1)")
    analysis_context = models.JSONField(null=True, blank=True, help_text="Context data used for classification")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['session', '-created_at']),
            models.Index(fields=['intent']),
        ]

    def __str__(self):
        return f"{self.session.telegram_user_id} - {self.intent} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"

class Emotion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(UserSession, on_delete=models.CASCADE, related_name='emotions')
    emotion_ratings = models.JSONField(help_text="Dictionary of emotion ratings: {emotion_code: rating(0-2)}")
    primary_emotion = models.CharField(
        max_length=32,
        choices=[(x[0], x[1]) for x in EMOTION_CHOICES],
        help_text="The strongest emotion detected"
    )
    messages_analyzed = models.PositiveIntegerField(default=10, help_text="Number of messages analyzed for this emotion detection")
    confidence_score = models.FloatField(null=True, blank=True, help_text="AI confidence in emotion detection (0-1)")
    analysis_context = models.JSONField(null=True, blank=True, help_text="Context data used for emotion detection")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['session', '-created_at']),
            models.Index(fields=['primary_emotion']),
        ]

    def __str__(self):
        return f"{self.session.telegram_user_id} - {self.primary_emotion} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"

    def get_emotion_summary(self):
        """Return a summary of detected emotions with ratings > 0"""
        summary = []
        for emotion_code, rating in self.emotion_ratings.items():
            if rating > 0:
                emotion_label = next((label for code, label, _ in EMOTION_CHOICES if code == emotion_code), emotion_code)
                rating_label = next((label for val, label, _ in EMOTION_RATING_CHOICES if val == rating), str(rating))
                summary.append(f"{emotion_label}: {rating_label}")
        return ", ".join(summary) if summary else "No emotions detected"

class RiskAssessment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(UserSession, on_delete=models.CASCADE, related_name='risk_assessments')
    risk_level = models.CharField(
        max_length=32,
        choices=[(x[0], x[1]) for x in RISK_LEVEL_CHOICES],
        help_text="The primary risk level detected"
    )
    risk_indicators = models.JSONField(null=True, blank=True, help_text="Specific indicators or keywords that triggered the risk assessment")
    severity_score = models.FloatField(null=True, blank=True, help_text="Risk severity score (0-1, where 1 is highest risk)")
    messages_analyzed = models.PositiveIntegerField(default=10, help_text="Number of messages analyzed for this risk assessment")
    confidence_score = models.FloatField(null=True, blank=True, help_text="AI confidence in risk assessment (0-1)")
    analysis_context = models.JSONField(null=True, blank=True, help_text="Context data used for risk assessment")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['session', '-created_at']),
            models.Index(fields=['risk_level']),
            models.Index(fields=['severity_score']),
        ]

    def __str__(self):
        return f"{self.session.telegram_user_id} - {self.risk_level} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"

    def get_risk_summary(self):
        """Return a summary of the risk assessment"""
        risk_label = next((label for code, label, _ in RISK_LEVEL_CHOICES if code == self.risk_level), self.risk_level)
        severity_text = ""
        if self.severity_score:
            if self.severity_score >= 0.8:
                severity_text = " (High Severity)"
            elif self.severity_score >= 0.5:
                severity_text = " (Medium Severity)"
            elif self.severity_score >= 0.2:
                severity_text = " (Low Severity)"
        
        return f"{risk_label}{severity_text}"

class MythAssessment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(UserSession, on_delete=models.CASCADE, related_name='myth_assessments')
    message = models.ForeignKey(ChatMessage, on_delete=models.CASCADE, related_name='myth_assessments')
    myth_type = models.CharField(
        max_length=32,
        choices=[(x[0], x[1]) for x in MYTH_DETECTION_CHOICES],
        help_text="The type of myth or misconception detected"
    )
    confidence_score = models.FloatField(null=True, blank=True, help_text="AI confidence in myth detection (0-1)")
    myth_detected = models.BooleanField(default=False, help_text="Whether any myth/misconception was detected")
    specific_myth = models.TextField(null=True, blank=True, help_text="Description of the specific myth detected")
    correction_provided = models.BooleanField(default=False, help_text="Whether correction was provided in response")
    severity_level = models.CharField(
        max_length=16,
        choices=[
            ('LOW', 'Low Impact'),
            ('MEDIUM', 'Medium Impact'), 
            ('HIGH', 'High Impact'),
            ('CRITICAL', 'Critical - Potentially Dangerous')
        ],
        null=True,
        blank=True,
        help_text="Severity of the misinformation impact"
    )
    analysis_context = models.JSONField(null=True, blank=True, help_text="Context data used for myth detection")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['session', '-created_at']),
            models.Index(fields=['myth_type']),
            models.Index(fields=['myth_detected']),
            models.Index(fields=['severity_level']),
        ]

    def __str__(self):
        return f"{self.session.telegram_user_id} - {self.myth_type} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"

    def get_myth_summary(self):
        """Return a summary of the myth assessment"""
        if not self.myth_detected:
            return "No myth detected"
        
        myth_label = next((label for code, label, _ in MYTH_DETECTION_CHOICES if code == self.myth_type), self.myth_type)
        
        severity_text = ""
        if self.severity_level:
            severity_text = f" ({self.severity_level.title()} Impact)"
        
        return f"{myth_label}{severity_text}"

    def is_cultural_myth(self):
        """Check if this is a cultural/traditional myth"""
        return self.myth_type.startswith('CULTURAL_')
    
    def is_medical_misconception(self):
        """Check if this is a medical misconception"""
        return self.myth_type.startswith('MEDICAL_')


