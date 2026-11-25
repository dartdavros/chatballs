function product_repo(name, component) {
    if (index(name, root) != 1) return 0
    component = substr(name, length(root) + 1)
    return component ~ /^(backend|frontend|gateway|postgres|updater)$/
}

# Порядок версий соответствует version_key в chatballs/updates/github.py.
function release(version) {
    return version ~ /^[0-9]+\.[0-9]+\.[0-9]+([.-][0-9A-Za-z.]+)?$/
}

function older(left, right, a, b, i, left_label, right_label) {
    split(left, a, /[.-]/)
    split(right, b, /[.-]/)
    for (i = 1; i <= 3; i++) {
        if (a[i] + 0 != b[i] + 0) return a[i] + 0 < b[i] + 0
    }
    left_label = index(left, "-") ? substr(left, index(left, "-") + 1) : ""
    right_label = index(right, "-") ? substr(right, index(right, "-") + 1) : ""
    return left_label != "" && (right_label == "" || "x" left_label < "x" right_label)
}

function expired(version) {
    return release(version) && older(version, current) &&
        (older(version, previous) || older(previous, version))
}

BEGIN {
    if (!release(previous) || !release(current) || !older(previous, current)) exit
    digest_pattern = "^sha256:[0-9a-f]{64}$"
}

$1 == "keep" && $2 ~ digest_pattern {
    protected_id[$2] = 1
    next
}

$1 == "keep" || $1 == "history" {
    split($2, ref, "@")
    split(ref[1], name, ":")
    if (!product_repo(name[1])) next
    if ($1 == "keep") {
        protected_ref[ref[1]] = 1
        if (ref[2] ~ digest_pattern) protected_ref[name[1] "@" ref[2]] = 1
    } else if (expired(name[2]) && ref[2] ~ digest_pattern) {
        old_digest[name[1] "@" ref[2]] = 1
    }
}

$1 == "image" && $5 ~ digest_pattern {
    repo = $2
    tag = $3
    digest = $4
    id = $5
    if (!product_repo(repo) || (id in image_repo && image_repo[id] != repo) ||
        (repo ":" tag in protected_ref) || (repo "@" digest in protected_ref)) {
        protected_id[id] = 1
        next
    }
    image_repo[id] = repo
    if (tag != "<none>") {
        if (expired(tag)) old_image[id] = 1
        else protected_id[id] = 1
    } else if (repo "@" digest in old_digest) {
        old_image[id] = 1
    }
}

END {
    for (id in old_image) {
        if (!(id in protected_id)) print id
    }
}
