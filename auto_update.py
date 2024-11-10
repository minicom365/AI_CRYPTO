import os
import subprocess
import sys
import git
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()


def has_updates(repo):
    """원격 리포지토리에 업데이트가 있는지 확인하는 함수."""
    origin = repo.remotes.origin
    origin.fetch()  # 원격 브랜치 정보를 가져옵니다.

    # 현재 브랜치와 원격 브랜치 비교
    local_commit = repo.head.commit
    remote_commit = origin.refs.master.commit  # 'master'를 원하는 브랜치로 변경 가능

    return local_commit != remote_commit  # 커밋이 다르면 업데이트가 존재함


def update_repo(repo_url: str, repo_path: str, username: str, password: str):
    try:
        # 비공식 리포지토리의 URL을 설정합니다.
        repo_url = repo_url.replace("//", f'//{username}:{password}@')

        repo = git.Repo(repo_path)
        if has_updates(repo):  # 업데이트 여부 확인
            origin = repo.remotes.origin
            origin.pull()
            print("업데이트 완료.")
            return True
        else:
            print("업데이트가 필요하지 않습니다.")

    except Exception as e:
        print(f"오류 발생: {e}")


def do_update():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    repo_url = os.getenv("GIT_REPO_URL")
    username = os.getenv("GIT_USERNAME")
    password = os.getenv("GIT_PASSWORD")

    if update_repo(repo_url, root_dir, username, password):
        try:
            # requirements.txt 파일 설치
            requirements_path = os.path.join(root_dir, 'requirements.txt')
            venv_python = os.path.join(root_dir, '.venv', 'Scripts', 'python.exe')

            subprocess.check_call([venv_python, "-m", "pip", "install", "-r", requirements_path])
            print("필요한 패키지가 성공적으로 설치되었습니다.")

            # 새 스크립트를 비동기적으로 실행
            subprocess.Popen([venv_python, os.path.join(root_dir, 'main.py')])
            print("새 코드가 성공적으로 실행되었습니다.")
            sys.exit()  # 현재 스크립트 종료

        except Exception as e:
            print(f"새 코드 실행 중 오류 발생: {e}")


if __name__ == "__main__":
    do_update()
