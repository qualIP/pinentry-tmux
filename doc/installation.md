# Installing pinentry-tmux

## Install uv

```sh
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Install pinentry-tmux

```sh
uv tool install "git+https://github.com/qualIP/pinentry-tmux"
```

## Confirm installation

```sh
ls -l "$HOME/.local/bin/pinentry-tmux"
```

*NOTE: If it's not there, you probably configured custom environment variables
and it can be found in one of the locations below. Please adapt instructions
accordingly.*

```sh
ls -l "$UV_TOOL_BIN_DIR/pinentry-tmux"
ls -l "$XDG_BIN_HOME/pinentry-tmux"
ls -l "$XDG_DATA_HOME/..bin/pinentry-tmux"
```

## Update gpg-agent.conf

Edit `$HOME/.gnupg/gpg-agent.conf` manually with your favorite editor to add
this line (with the exact path substituted):

```
pinentry-program /home/user/.local/bin/pinentry-tmux
```

*Or,* run these commands to comment any old pinentry-program configuration and
add the pinentry-tmux line:

```sh
sed -i -e 's/^pinentry-program/#&/' "$HOME/.gnupg/gpg-agent.conf"
echo "pinentry-program $HOME/.local/bin/pinentry-tmux" >> "$HOME/.gnupg/gpg-agent.conf"
```

Reload your gpg-agent's configuration:

```sh
gpgconf --reload gpg-agent
```

## Try it out

Try it out with any gpg operation requiring your passphrase, such as:

```sh
echo test | gpg --sign > /dev/null
```

If you get a graphical interface, `unset DISPLAY` and try again.

# Uninstalling pinentry-tmux

## Uninstall pinentry-tmux

```sh
uv tool uninstall pinentry-tmux
```

## Update gpg-agent.conf

Edit `$HOME/.gnupg/gpg-agent.conf` manually with your favorite editor to remove the pinentry-tmux line and restore/uncomment any previous pinentry configuration.

Reload your gpg-agent's configuration:

```sh
gpgconf --reload gpg-agent
```
