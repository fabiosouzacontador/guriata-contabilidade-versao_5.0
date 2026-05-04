"""
Service de Usuário
Contém toda a regra de negócio relacionada a usuários
"""

from sqlmodel import select, Session
from typing import Optional, List
from src.models.usuario_model import Usuario
from src.utils import hash_senha, verificar_senha, migrar_senha_plana_para_hash


class UsuarioService:
    """Service para operações de usuário"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def buscar_por_username(self, username: str) -> Optional[Usuario]:
        """Busca usuário por username"""
        return self.session.exec(
            select(Usuario).where(Usuario.username == username)
        ).first()
    
    def buscar_por_id(self, user_id: int) -> Optional[Usuario]:
        """Busca usuário por ID"""
        return self.session.get(Usuario, user_id)
    
    def listar_todos(self) -> List[Usuario]:
        """Lista todos os usuários"""
        return self.session.exec(select(Usuario)).all()
    
    def criar_usuario(
        self,
        username: str,
        senha: str,
        nome: str,
        perfil: str,
        termos_aceitos: bool = True,
        escola_id: Optional[int] = None,
        turma_id: Optional[int] = None,
        criado_por_id: Optional[int] = None
    ) -> Usuario:
        """Cria um novo usuário com senha hasheada"""
        if self.buscar_por_username(username):
            raise ValueError(f"Username '{username}' já está em uso")
        
        senha_hash = hash_senha(senha)
        
        usuario = Usuario(
            username=username,
            senha=senha_hash,
            nome=nome,
            perfil=perfil,
            termos_aceitos=termos_aceitos,
            escola_id=escola_id,
            turma_id=turma_id,
            criado_por_id=criado_por_id,
            xp=0
        )
        
        self.session.add(usuario)
        self.session.commit()
        self.session.refresh(usuario)
        
        return usuario
    
    def autenticar(self, username: str, senha: str) -> Optional[Usuario]:
        """Autentica usuário verificando senha"""
        usuario = self.buscar_por_username(username)
        
        if not usuario:
            return None
        
        senha_armazenada = migrar_senha_plana_para_hash(usuario.senha)
        
        if senha_armazenada != usuario.senha:
            usuario.senha = senha_armazenada
            self.session.add(usuario)
            self.session.commit()
        
        if verificar_senha(senha, senha_armazenada):
            return usuario
        
        return None
    
    def alterar_senha(self, user_id: int, nova_senha: str) -> bool:
        """Altera a senha de um usuário"""
        usuario = self.buscar_por_id(user_id)
        
        if not usuario:
            return False
        
        usuario.senha = hash_senha(nova_senha)
        self.session.add(usuario)
        self.session.commit()
        
        return True
    
    def deletar_usuario(self, user_id: int) -> bool:
        """Deleta um usuário"""
        usuario = self.buscar_por_id(user_id)
        
        if not usuario:
            return False
        
        self.session.delete(usuario)
        self.session.commit()
        
        return True
    
    def atualizar_xp(self, user_id: int, pontos: int) -> Optional[Usuario]:
        """Atualiza XP do usuário"""
        usuario = self.buscar_por_id(user_id)
        
        if not usuario:
            return None
        
        usuario.xp += pontos
        self.session.add(usuario)
        self.session.commit()
        self.session.refresh(usuario)
        
        return usuario
