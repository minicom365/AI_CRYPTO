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


def update_repo(repo_url: str, repo_path: str, username: str = None, password: str = None):
    """원격 리포지토리를 업데이트하거나 클론하는 함수."""
    try:
        # 인증 정보가 제공된 경우 URL에 포함
        if username and password:
            repo_url = repo_url.replace("//", f"//{username}:{password}@")
            # print("인증 정보를 사용하여 URL을 설정했습니다.")

        # 로컬 경로에 리포지토리가 없는 경우 클론
        if not os.path.exists(os.path.join(repo_path, ".git")):
            print(f"리포지토리가 존재하지 않습니다. {repo_url}에서 클론을 생성합니다.")
            git.Repo.clone_from(repo_url, repo_path)
            return True

        # 기존 리포지토리 업데이트
        repo = git.Repo(repo_path)
        if has_updates(repo):  # 업데이트 여부 확인
            print("업데이트가 발견되었습니다. 로컬 브랜치를 원격 브랜치로 재설정합니다.")
            repo.git.reset('--hard', 'origin/master')
            print("업데이트 완료.")
            return True
        else:
            # print("업데이트가 필요하지 않습니다.")
            pass
    except Exception as e:
        print(f"리포지토리 업데이트 중 오류 발생: {e}")


def do_update(args: list = sys.argv):
    root_dir = os.path.dirname(os.path.abspath(__file__))
    repo_url = os.getenv("GIT_REPO_URL")
    username = os.getenv("GIT_USERNAME", None)  # 환경 변수에서 가져오거나 None
    password = os.getenv("GIT_PASSWORD", None)  # 환경 변수에서 가져오거나 None

    if update_repo(repo_url, root_dir, username, password):
        try:
            # requirements.txt 파일 설치
            requirements_path = os.path.join(root_dir, 'requirements.txt')
            python = sys.executable

            subprocess.check_call([python, "-m", "pip", "install", "-r", requirements_path])
            print("필요한 패키지가 성공적으로 설치되었습니다.")

            # 새 스크립트를 비동기적으로 실행
            print([python, os.path.join(root_dir, args[0]), *args[1:]])
            subprocess.Popen([python, os.path.join(root_dir, args[0]), *args[1:]])
            print("새 코드가 성공적으로 실행되었습니다.")
            sys.exit()  # 현재 스크립트 종료

        except Exception as e:
            print(f"새 코드 실행 중 오류 발생: {e}")


if __name__ == "__main__":
    do_update()
