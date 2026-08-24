import { ChatAvatar } from "../../components/chat/ChatWidget";
import { FaqAccordion, type FaqItem } from "../../components/support/FaqAccordion";
import { OpenChatButton } from "../../components/support/OpenChatButton";
import { SystemStatusBar } from "../../components/support/SystemStatusBar";

const faqItems: FaqItem[] = [
  {
    question: "Bekleyen emrimi nereden takip edebilirim?",
    answer:
      "İşlemler sayfasındaki 'Emir Durumu' alanından bekleyen ve tamamlanan emirleri görüntüleyebilirsin.",
  },
  {
    question: "Portföy değerim ne zaman güncellenir?",
    answer:
      "Demo arayüzdeki değerler temsilidir. Canlı sistemde piyasa verisine bağlı olarak işlem saatleri boyunca güncellenir.",
  },
  {
    question: "Şüpheli bir işlem görürsem ne yapmalıyım?",
    answer:
      "Hiçbir doğrulama kodunu paylaşmadan 7/24 destek hattını ara ve ilgili işlemi destek uzmanına bildir.",
  },
];

const priorityTopics = [
  "Hesap ve giriş işlemleri",
  "Emir ve işlem takibi",
  "Para yatırma / çekme",
  "Güvenlik ve kimlik doğrulama",
  "Ücretler ve komisyonlar",
];

const securityTips = [
  "Doğrulama kodunu (OTP) hiçbir kanaldan, hiç kimseyle paylaşma.",
  "Şifreni düzenli aralıklarla güncelle ve başka hiçbir hesapta kullanma.",
  "Herkese açık Wi-Fi ağlarında işlem yapmaktan kaçın.",
  "Beklenmedik bağlantı ve eklere tıklamadan önce gönderenin kimliğini doğrula.",
];

const securityAlerts = [
  {
    icon: "⚠️",
    title: "Sahte Bültenlere Dikkat",
    description:
      "Resmi olmayan kaynaklardan gelen yatırım tavsiyesi içeren bültenlere güvenme, her zaman uygulama içi kaynaklarımızı kontrol et.",
  },
  {
    icon: "🔗",
    title: "Yetkisiz Linklere Tıklama",
    description:
      "E-posta veya mesajla gelen, kimliğini doğrulamanı isteyen linklere tıklamadan önce gönderenin resmi POLIFIN kanalı olduğundan emin ol.",
  },
  {
    icon: "🔒",
    title: "Şifreni ve Kodlarını Paylaşma",
    description: "Hiçbir POLIFIN çalışanı senden şifreni, SMS doğrulama kodunu veya PIN'ini telefonda ya da yazıyla istemez.",
  },
];

function MaskIcon({ src }: { src: string }) {
  return (
    <span
      aria-hidden="true"
      className="h-[58%] w-[58%] bg-current"
      style={{
        maskImage: `url(${src})`,
        maskPosition: "center",
        maskRepeat: "no-repeat",
        maskSize: "contain",
        WebkitMaskImage: `url(${src})`,
        WebkitMaskPosition: "center",
        WebkitMaskRepeat: "no-repeat",
        WebkitMaskSize: "contain",
      }}
    />
  );
}

function CheckShieldIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 3l7 3v5c0 4.5-3 8.4-7 10-4-1.6-7-5.5-7-10V6z" />
      <path d="M9 12l2 2 4-4" />
    </svg>
  );
}

function ChevronIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 6l6 6-6 6" />
    </svg>
  );
}

export default function DestekPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold app-heading">Destek</h1>
        <p className="mt-1 text-sm app-muted">Sana nasıl yardımcı olabiliriz?</p>
      </div>

      <SystemStatusBar />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        <div className="rounded-xl border app-card p-5 shadow-sm">
          <span className="grid h-10 w-10 place-items-center rounded-lg app-primary-soft">
            <MaskIcon src="/icons/telefon.png" />
          </span>
          <h2 className="mt-3 text-base font-semibold app-heading">Telefon Desteği</h2>
          <p className="mt-1 text-sm app-muted">
            Uzmanlarımıza 7/24 ulaşabilir, hesabınla ilgili her konuda destek alabilirsin.
          </p>
          <a
            href="tel:+908502552000"
            className="mt-3 inline-flex items-center gap-1.5 text-sm font-semibold app-primary-text"
          >
            0850 255 20 00
          </a>
        </div>

        <div className="rounded-xl border app-card p-5 shadow-sm">
          <span className="grid h-10 w-10 place-items-center rounded-lg app-primary-soft">
            <MaskIcon src="/icons/eposta.png" />
          </span>
          <h2 className="mt-3 text-base font-semibold app-heading">E-posta Desteği</h2>
          <p className="mt-1 text-sm app-muted">
            Aciliyeti olmayan taleplerini e-posta ile iletebilir, 24 saat içinde yanıt alabilirsin.
          </p>
          <a href="mailto:destek@polifin.com" className="mt-3 inline-flex items-center gap-1.5 text-sm font-semibold app-primary-text">
            destek@polifin.com
          </a>
        </div>

        <div className="rounded-xl border app-card p-5 shadow-sm">
          <span className="block h-10 w-10 shrink-0">
            <ChatAvatar />
          </span>
          <h2 className="mt-3 text-base font-semibold app-heading">AI Finans Asistanı</h2>
          <p className="mt-1 text-sm app-muted">
            Piyasa, portföy ve işlemlerinle ilgili sorularını yapay zeka destekli asistanımıza anında sorabilirsin.
          </p>
          <OpenChatButton className="mt-3 inline-flex items-center gap-1.5 text-sm font-semibold app-primary-text">
            Sohbeti başlat
          </OpenChatButton>
        </div>
      </div>

      <div className="rounded-xl border app-card p-5 shadow-sm">
        <h2 className="text-base font-semibold app-heading">Öncelikli Destek Konuları</h2>
        <ul className="mt-4 space-y-2 text-sm">
          {priorityTopics.map((topic) => (
            <li
              key={topic}
              className="flex items-center justify-between gap-3 rounded-lg app-card-muted p-3 app-heading"
            >
              {topic}
              <span className="app-muted">
                <ChevronIcon />
              </span>
            </li>
          ))}
        </ul>
      </div>

      <div className="rounded-xl border app-card p-5 shadow-sm">
        <h2 className="text-base font-semibold app-heading">Güvenliğin İçin</h2>
        <ul className="mt-4 grid gap-3 sm:grid-cols-2">
          {securityTips.map((tip) => (
            <li key={tip} className="flex items-start gap-3 rounded-lg app-card-muted p-3 text-sm app-muted">
              <span className="mt-0.5 shrink-0 app-success">
                <CheckShieldIcon />
              </span>
              {tip}
            </li>
          ))}
        </ul>
      </div>

      <div className="rounded-xl border app-card p-5 shadow-sm">
        <h2 className="text-base font-semibold app-heading">🛡️ Güvenlik İpuçları</h2>
        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          {securityAlerts.map((alert) => (
            <div key={alert.title} className="rounded-lg border app-warning-box p-4">
              <span className="text-xl">{alert.icon}</span>
              <h3 className="mt-2 text-sm font-semibold">{alert.title}</h3>
              <p className="mt-1 text-xs leading-relaxed">{alert.description}</p>
            </div>
          ))}
        </div>
      </div>

      <section id="sss" className="scroll-mt-24 rounded-xl border app-card p-5 shadow-sm">
        <h2 className="text-base font-semibold app-heading">Sık Sorulan Sorular</h2>
        <p className="mt-1 text-sm app-muted">En çok sorulan konulara hızlı yanıtlar</p>
        <div className="mt-4">
          <FaqAccordion items={faqItems} />
        </div>
      </section>
    </div>
  );
}
