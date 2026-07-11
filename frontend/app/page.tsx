import Link from "next/link";

export default function Home() {
  return (
    <div>
      <h1>MUSE 菜单整理后台</h1>
      <p className="muted">
        客服把客户聊天逐条转发给机器人后，在这里选客户、提交给 AI 整理、审查后入库。
      </p>
      <p>
        <Link href="/inbox">→ 进入待整理收件箱</Link>
      </p>
    </div>
  );
}
